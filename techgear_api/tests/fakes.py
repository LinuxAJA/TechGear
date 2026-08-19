"""Repositorios falsos en memoria.

Implementan la misma interfaz que los repositorios reales, pero guardando los
datos en un diccionario de Python. Gracias a ellos, las reglas de negocio se
prueban en milisegundos, sin conexion a MongoDB Atlas y sin dejar residuos.

Esta es la razon practica de haber separado la capa de datos: si los servicios
hablaran directamente con Motor, no habria forma de probarlos asi.
"""

import copy
from datetime import datetime
from typing import Any

from bson import ObjectId

from app.core.exceptions import DuplicateOrderNumberError, DuplicateSkuError


class InMemoryProductRepository:
    """Version en memoria de ProductRepository."""

    def __init__(self) -> None:
        self.documents: dict[str, dict[str, Any]] = {}

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        if any(document["sku"] == data["sku"] for document in self.documents.values()):
            raise DuplicateSkuError(data["sku"])

        product_id = str(ObjectId())
        document = copy.deepcopy(data)
        document["_id"] = product_id
        self.documents[product_id] = document
        return copy.deepcopy(document)

    async def get_by_id(self, product_id: str) -> dict[str, Any] | None:
        document = self.documents.get(product_id)
        return copy.deepcopy(document) if document else None

    async def get_by_sku(self, sku: str) -> dict[str, Any] | None:
        for document in self.documents.values():
            if document["sku"] == sku:
                return copy.deepcopy(document)
        return None

    async def list_products(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
        category: str | None = None,
        only_active: bool = True,
    ) -> tuple[list[dict[str, Any]], int]:
        results = list(self.documents.values())
        if only_active:
            results = [document for document in results if document["is_active"]]
        if category:
            results = [document for document in results if document["category"] == category]
        if search:
            needle = search.lower()
            results = [
                document
                for document in results
                if needle in document["name"].lower()
                or needle in document["sku"].lower()
                or needle in document.get("description", "").lower()
            ]
        total = len(results)
        return copy.deepcopy(results[skip : skip + limit]), total

    async def update(self, product_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
        document = self.documents.get(product_id)
        if document is None:
            return None
        document.update(copy.deepcopy(changes))
        return copy.deepcopy(document)

    async def deactivate(self, product_id: str, *, updated_at: datetime) -> bool:
        document = self.documents.get(product_id)
        if document is None:
            return False
        document["is_active"] = False
        document["updated_at"] = updated_at
        return True

    async def decrement_stock(
        self, product_id: str, quantity: int, *, updated_at: datetime
    ) -> dict[str, Any] | None:
        document = self.documents.get(product_id)
        # Misma condicion que el filtro atomico del repositorio real.
        if document is None or not document["is_active"] or document["stock"] < quantity:
            return None
        document["stock"] -= quantity
        document["updated_at"] = updated_at
        return copy.deepcopy(document)

    async def restore_stock(self, product_id: str, quantity: int, *, updated_at: datetime) -> None:
        document = self.documents.get(product_id)
        if document is None:
            return
        document["stock"] += quantity
        document["updated_at"] = updated_at


class InMemoryOrderRepository:
    """Version en memoria de OrderRepository."""

    def __init__(self) -> None:
        self.documents: dict[str, dict[str, Any]] = {}

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        if any(document["order_number"] == data["order_number"] for document in self.documents.values()):
            raise DuplicateOrderNumberError(data["order_number"])

        order_id = str(ObjectId())
        document = copy.deepcopy(data)
        document["_id"] = order_id
        self.documents[order_id] = document
        return copy.deepcopy(document)

    async def get_by_id(self, order_id: str) -> dict[str, Any] | None:
        document = self.documents.get(order_id)
        return copy.deepcopy(document) if document else None

    async def list_orders(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        customer: str | None = None,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        results = list(self.documents.values())
        if customer:
            results = [document for document in results if document["customer"]["username"] == customer]
        if status:
            results = [document for document in results if document["status"] == status]
        total = len(results)
        return copy.deepcopy(results[skip : skip + limit]), total

    async def update_status(
        self, order_id: str, status: str, *, updated_at: datetime
    ) -> dict[str, Any] | None:
        document = self.documents.get(order_id)
        if document is None:
            return None
        document["status"] = status
        document["updated_at"] = updated_at
        return copy.deepcopy(document)
