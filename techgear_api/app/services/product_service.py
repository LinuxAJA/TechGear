"""Reglas de negocio del Producto.

El servicio no sabe que existe HTTP ni que existe MongoDB. Recibe esquemas
Pydantic o valores simples, aplica las reglas y lanza excepciones de dominio.
Por eso puede probarse con un repositorio falso en memoria, sin conexion a
Atlas y en milisegundos.
"""

from typing import Any

from app.core.exceptions import DuplicateSkuError, ProductNotFoundError
from app.core.utils import utcnow
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    """Casos de uso del catalogo de productos."""

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    async def create_product(self, payload: ProductCreate) -> dict[str, Any]:
        """Registra un producto nuevo.

        El SKU se verifica antes de insertar para poder responder un mensaje
        claro; el indice unico de la base es la garantia definitiva ante
        peticiones simultaneas.
        """
        if await self._repository.get_by_sku(payload.sku) is not None:
            raise DuplicateSkuError(payload.sku)

        now = utcnow()
        data = payload.model_dump()
        data["is_active"] = True
        data["created_at"] = now
        data["updated_at"] = now

        return await self._repository.create(data)

    async def get_product(self, product_id: str) -> dict[str, Any]:
        """Devuelve un producto o falla si no existe."""
        product = await self._repository.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        return product

    async def list_products(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
        category: str | None = None,
        only_active: bool = True,
    ) -> tuple[list[dict[str, Any]], int]:
        """Devuelve una pagina del catalogo."""
        return await self._repository.list_products(
            skip=skip,
            limit=limit,
            search=search,
            category=category,
            only_active=only_active,
        )

    async def update_product(self, product_id: str, payload: ProductUpdate) -> dict[str, Any]:
        """Aplica una actualizacion parcial.

        exclude_unset=True es la clave del comportamiento PATCH: solo viajan
        los campos que el cliente envio explicitamente, de modo que los demas
        conservan su valor en vez de sobrescribirse con null.
        """
        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            return await self.get_product(product_id)

        changes["updated_at"] = utcnow()
        updated = await self._repository.update(product_id, changes)
        if updated is None:
            raise ProductNotFoundError(product_id)
        return updated

    async def deactivate_product(self, product_id: str) -> None:
        """Retira un producto del catalogo mediante borrado logico."""
        deactivated = await self._repository.deactivate(product_id, updated_at=utcnow())
        if not deactivated:
            raise ProductNotFoundError(product_id)
