"""Capa de datos del Pedido."""

from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.exceptions import DuplicateOrderNumberError
from app.db.mongodb import ORDERS_COLLECTION
from app.repositories.mappers import from_mongo, to_mongo, to_object_id


class OrderRepository:
    """Operaciones de persistencia sobre la coleccion de pedidos."""

    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self._collection = database[ORDERS_COLLECTION]

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Inserta un pedido ya calculado por el servicio."""
        document = to_mongo(data)
        try:
            result = await self._collection.insert_one(document)
        except DuplicateKeyError as error:
            raise DuplicateOrderNumberError(str(data.get("order_number"))) from error

        document["_id"] = result.inserted_id
        return from_mongo(document)

    async def get_by_id(self, order_id: str) -> dict[str, Any] | None:
        """Busca un pedido por su identificador."""
        object_id = to_object_id(order_id)
        if object_id is None:
            return None
        document = await self._collection.find_one({"_id": object_id})
        return from_mongo(document) if document else None

    async def list_orders(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        customer: str | None = None,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Devuelve una pagina de pedidos y el total que cumple el filtro.

        El filtro por customer usa el username del portal Django, que es lo que
        permite construir la vista "Mis pedidos" sin duplicar los usuarios en
        MongoDB.
        """
        filters: dict[str, Any] = {}
        if customer:
            filters["customer.username"] = customer
        if status:
            filters["status"] = status

        total = await self._collection.count_documents(filters)
        cursor = self._collection.find(filters).sort("created_at", -1).skip(skip).limit(limit)
        items = [from_mongo(document) async for document in cursor]
        return items, total

    async def update_status(
        self, order_id: str, status: str, *, updated_at: datetime
    ) -> dict[str, Any] | None:
        """Cambia el estado del pedido y devuelve el documento actualizado."""
        object_id = to_object_id(order_id)
        if object_id is None:
            return None

        document = await self._collection.find_one_and_update(
            {"_id": object_id},
            {"$set": {"status": status, "updated_at": updated_at}},
            return_document=ReturnDocument.AFTER,
        )
        return from_mongo(document) if document else None
