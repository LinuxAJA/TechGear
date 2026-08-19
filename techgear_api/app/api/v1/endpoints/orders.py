"""Endpoints de pedidos."""

from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import OrderServiceDep
from app.schemas.common import OBJECT_ID_PATTERN, ErrorResponse, Page
from app.schemas.order import OrderCreate, OrderPublic, OrderStatus, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["Pedidos"])

OrderIdPath = Annotated[
    str,
    Path(
        description="Identificador del pedido (ObjectId de MongoDB)",
        pattern=OBJECT_ID_PATTERN,
        examples=["66c1f4b7e8b1a2d4f0c9e456"],
    ),
]


@router.post(
    "",
    response_model=OrderPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un pedido",
    description=(
        "Crea un pedido a partir de los identificadores de producto y las cantidades. "
        "El precio NO se recibe del cliente: el servidor lo lee de la base de datos, "
        "calcula los subtotales y el total, y descuenta el inventario de forma atomica. "
        "Cada linea guarda una copia del SKU, el nombre y el precio vigentes en el momento "
        "de la compra."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Alguno de los productos no existe"},
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Stock insuficiente o producto retirado del catalogo",
        },
    },
)
async def create_order(payload: OrderCreate, service: OrderServiceDep) -> OrderPublic:
    """Registra un pedido."""
    order = await service.create_order(payload)
    return OrderPublic.model_validate(order)


@router.get(
    "",
    response_model=Page[OrderPublic],
    summary="Listar pedidos",
    description="Devuelve una pagina de pedidos. Permite filtrar por comprador y por estado.",
)
async def list_orders(
    service: OrderServiceDep,
    skip: Annotated[int, Query(ge=0, description="Cantidad de pedidos a omitir")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Tamano maximo de la pagina")] = 20,
    customer: Annotated[
        str | None, Query(description="Filtra por el nombre de usuario del comprador")
    ] = None,
    order_status: Annotated[
        OrderStatus | None, Query(alias="status", description="Filtra por estado del pedido")
    ] = None,
) -> Page[OrderPublic]:
    """Lista los pedidos de forma paginada."""
    items, total = await service.list_orders(
        skip=skip,
        limit=limit,
        customer=customer,
        status=order_status.value if order_status else None,
    )
    return Page[OrderPublic](items=items, total=total, skip=skip, limit=limit)


@router.get(
    "/{order_id}",
    response_model=OrderPublic,
    summary="Consultar un pedido",
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "El pedido no existe"},
    },
)
async def get_order(order_id: OrderIdPath, service: OrderServiceDep) -> OrderPublic:
    """Consulta un pedido."""
    order = await service.get_order(order_id)
    return OrderPublic.model_validate(order)


@router.patch(
    "/{order_id}/status",
    response_model=OrderPublic,
    summary="Cambiar el estado de un pedido",
    description=(
        "Aplica una transicion de estado valida:\n\n"
        "- `pending` -> `paid` o `cancelled`\n"
        "- `paid` -> `shipped` o `cancelled`\n"
        "- `shipped` -> `delivered`\n"
        "- `delivered` y `cancelled` son estados finales\n\n"
        "Cancelar un pedido devuelve las unidades reservadas al inventario."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "El pedido no existe"},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "La transicion de estado no es valida"},
    },
)
async def update_order_status(
    order_id: OrderIdPath,
    payload: OrderStatusUpdate,
    service: OrderServiceDep,
) -> OrderPublic:
    """Cambia el estado de un pedido."""
    order = await service.update_status(order_id, payload.status)
    return OrderPublic.model_validate(order)
