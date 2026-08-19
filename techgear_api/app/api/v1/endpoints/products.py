"""Endpoints del catalogo de productos.

Los endpoints solo traducen HTTP: leen parametros, delegan en el servicio y
devuelven el esquema de salida. No contienen reglas de negocio ni consultas a
MongoDB, y no capturan errores: las excepciones de dominio las traducen los
manejadores globales registrados en app/core/handlers.py.
"""

from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import ProductServiceDep
from app.schemas.common import OBJECT_ID_PATTERN, ErrorResponse, Page
from app.schemas.product import Category, ProductCreate, ProductPublic, ProductUpdate

router = APIRouter(prefix="/products", tags=["Productos"])

ProductIdPath = Annotated[
    str,
    Path(
        description="Identificador del producto (ObjectId de MongoDB)",
        pattern=OBJECT_ID_PATTERN,
        examples=["66c1f3a2e8b1a2d4f0c9e123"],
    ),
]


@router.get(
    "",
    response_model=Page[ProductPublic],
    summary="Listar productos del catalogo",
    description=(
        "Devuelve una pagina de productos. Permite buscar por texto en el nombre, el SKU "
        "y la descripcion, filtrar por categoria y decidir si se incluyen los productos "
        "retirados del catalogo."
    ),
)
async def list_products(
    service: ProductServiceDep,
    skip: Annotated[int, Query(ge=0, description="Cantidad de productos a omitir")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Tamano maximo de la pagina")] = 20,
    q: Annotated[str | None, Query(description="Texto a buscar en nombre, SKU o descripcion")] = None,
    category: Annotated[Category | None, Query(description="Filtra por categoria")] = None,
    only_active: Annotated[bool, Query(description="Muestra solo los productos activos")] = True,
) -> Page[ProductPublic]:
    """Lista el catalogo de forma paginada."""
    items, total = await service.list_products(
        skip=skip,
        limit=limit,
        search=q,
        category=category.value if category else None,
        only_active=only_active,
    )
    return Page[ProductPublic](items=items, total=total, skip=skip, limit=limit)


@router.post(
    "",
    response_model=ProductPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un producto",
    description="Registra un producto nuevo en el catalogo. El SKU debe ser unico.",
    responses={
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "Ya existe un producto con ese SKU"},
    },
)
async def create_product(payload: ProductCreate, service: ProductServiceDep) -> ProductPublic:
    """Crea un producto."""
    product = await service.create_product(payload)
    return ProductPublic.model_validate(product)


@router.get(
    "/{product_id}",
    response_model=ProductPublic,
    summary="Consultar un producto",
    description="Devuelve un producto por su identificador, este activo o no.",
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "El producto no existe"},
    },
)
async def get_product(product_id: ProductIdPath, service: ProductServiceDep) -> ProductPublic:
    """Consulta un producto."""
    product = await service.get_product(product_id)
    return ProductPublic.model_validate(product)


@router.patch(
    "/{product_id}",
    response_model=ProductPublic,
    summary="Actualizar un producto",
    description=(
        "Actualiza parcialmente un producto. Solo se modifican los campos enviados; "
        "los omitidos conservan su valor actual."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "El producto no existe"},
    },
)
async def update_product(
    product_id: ProductIdPath,
    payload: ProductUpdate,
    service: ProductServiceDep,
) -> ProductPublic:
    """Actualiza un producto."""
    product = await service.update_product(product_id, payload)
    return ProductPublic.model_validate(product)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Retirar un producto del catalogo",
    description=(
        "Aplica borrado logico: el producto deja de aparecer en el catalogo pero el "
        "documento se conserva, porque los pedidos historicos lo referencian."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "El producto no existe"},
    },
)
async def delete_product(product_id: ProductIdPath, service: ProductServiceDep) -> None:
    """Desactiva un producto."""
    await service.deactivate_product(product_id)
