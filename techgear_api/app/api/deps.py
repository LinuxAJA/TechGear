"""Inyeccion de dependencias de la capa HTTP.

Los endpoints no construyen repositorios ni servicios: los reciben ya armados.
Ademas de leerse mejor, esto permite sustituirlos en las pruebas mediante
app.dependency_overrides sin tocar el codigo de produccion.
"""

from typing import Annotated

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_database
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.services.order_service import OrderService
from app.services.product_service import ProductService

DatabaseDep = Annotated[AsyncIOMotorDatabase, Depends(get_database)]


# ── Repositorios ──────────────────────────────────────────
def get_product_repository(database: DatabaseDep) -> ProductRepository:
    """Construye el repositorio de productos."""
    return ProductRepository(database)


ProductRepositoryDep = Annotated[ProductRepository, Depends(get_product_repository)]


def get_order_repository(database: DatabaseDep) -> OrderRepository:
    """Construye el repositorio de pedidos."""
    return OrderRepository(database)


OrderRepositoryDep = Annotated[OrderRepository, Depends(get_order_repository)]


# ── Servicios ─────────────────────────────────────────────
def get_product_service(repository: ProductRepositoryDep) -> ProductService:
    """Construye el servicio de productos."""
    return ProductService(repository)


ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]


def get_order_service(
    orders: OrderRepositoryDep,
    products: ProductRepositoryDep,
) -> OrderService:
    """Construye el servicio de pedidos.

    Necesita ambos repositorios: registra el pedido y, al mismo tiempo, mueve
    el inventario de los productos involucrados.
    """
    return OrderService(orders, products)


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
