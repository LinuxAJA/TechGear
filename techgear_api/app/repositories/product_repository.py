"""Capa de datos del Producto.

Junto con app/db/, este es el unico lugar que conoce Motor, BSON y la forma de
los documentos. Recibe y devuelve diccionarios de Python: los servicios no ven
ObjectId ni Decimal128.
"""

import re
from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.exceptions import DuplicateSkuError
from app.db.mongodb import PRODUCTS_COLLECTION
from app.repositories.mappers import from_mongo, to_mongo, to_object_id


class ProductRepository:
    """Operaciones de persistencia sobre la coleccion de productos."""

    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self._collection = database[PRODUCTS_COLLECTION]

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Inserta un producto y devuelve el documento resultante."""
        document = to_mongo(data)
        try:
            result = await self._collection.insert_one(document)
        except DuplicateKeyError as error:
            # El indice unico sobre sku es la garantia real: protege incluso
            # cuando dos peticiones simultaneas pasan la validacion previa.
            raise DuplicateSkuError(str(data.get("sku"))) from error

        document["_id"] = result.inserted_id
        return from_mongo(document)

    async def get_by_id(self, product_id: str) -> dict[str, Any] | None:
        """Busca un producto por su identificador."""
        object_id = to_object_id(product_id)
        if object_id is None:
            return None
        document = await self._collection.find_one({"_id": object_id})
        return from_mongo(document) if document else None

    async def get_by_sku(self, sku: str) -> dict[str, Any] | None:
        """Busca un producto por su codigo de inventario."""
        document = await self._collection.find_one({"sku": sku})
        return from_mongo(document) if document else None

    async def list_products(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
        category: str | None = None,
        only_active: bool = True,
    ) -> tuple[list[dict[str, Any]], int]:
        """Devuelve una pagina de productos y el total que cumple el filtro."""
        filters: dict[str, Any] = {}

        if only_active:
            filters["is_active"] = True
        if category:
            filters["category"] = category
        if search:
            # re.escape es obligatorio: sin el, un usuario podria enviar
            # caracteres especiales de expresion regular y alterar la consulta
            # o provocar una busqueda desproporcionadamente costosa.
            pattern = re.escape(search)
            filters["$or"] = [
                {"name": {"$regex": pattern, "$options": "i"}},
                {"sku": {"$regex": pattern, "$options": "i"}},
                {"description": {"$regex": pattern, "$options": "i"}},
            ]

        total = await self._collection.count_documents(filters)
        cursor = self._collection.find(filters).sort("created_at", -1).skip(skip).limit(limit)
        items = [from_mongo(document) async for document in cursor]
        return items, total

    async def update(self, product_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
        """Aplica cambios parciales y devuelve el documento ya actualizado."""
        object_id = to_object_id(product_id)
        if object_id is None:
            return None

        document = await self._collection.find_one_and_update(
            {"_id": object_id},
            {"$set": to_mongo(changes)},
            return_document=ReturnDocument.AFTER,
        )
        return from_mongo(document) if document else None

    async def deactivate(self, product_id: str, *, updated_at: datetime) -> bool:
        """Aplica borrado logico.

        No se elimina el documento porque los pedidos historicos referencian
        productos: borrarlos fisicamente dejaria pedidos huerfanos.
        """
        object_id = to_object_id(product_id)
        if object_id is None:
            return False

        result = await self._collection.update_one(
            {"_id": object_id},
            {"$set": {"is_active": False, "updated_at": updated_at}},
        )
        return result.matched_count == 1

    async def decrement_stock(
        self, product_id: str, quantity: int, *, updated_at: datetime
    ) -> dict[str, Any] | None:
        """Descuenta unidades de forma atomica y condicional.

        La condicion "stock >= quantity" viaja DENTRO del filtro, no en un if
        previo. Consultar primero y actualizar despues seria una condicion de
        carrera: dos pedidos simultaneos podrian dejar el inventario negativo.
        MongoDB garantiza que la actualizacion de un documento es atomica.

        Devuelve el documento ya descontado, o None si el producto no existe,
        esta inactivo o no tiene unidades suficientes. Distinguir cual de los
        tres casos ocurrio es tarea del servicio.
        """
        object_id = to_object_id(product_id)
        if object_id is None:
            return None

        document = await self._collection.find_one_and_update(
            {"_id": object_id, "is_active": True, "stock": {"$gte": quantity}},
            {"$inc": {"stock": -quantity}, "$set": {"updated_at": updated_at}},
            return_document=ReturnDocument.AFTER,
        )
        return from_mongo(document) if document else None

    async def restore_stock(self, product_id: str, quantity: int, *, updated_at: datetime) -> None:
        """Devuelve unidades al inventario.

        Se usa como transaccion compensatoria: si un pedido falla a mitad de
        camino, hay que reponer lo que ya se habia descontado.
        """
        object_id = to_object_id(product_id)
        if object_id is None:
            return

        await self._collection.update_one(
            {"_id": object_id},
            {"$inc": {"stock": quantity}, "$set": {"updated_at": updated_at}},
        )
