"""Creacion de indices de las colecciones.

Se ejecuta en el arranque de la aplicacion. create_index es idempotente: si el
indice ya existe, MongoDB no hace nada. Por eso no hace falta un sistema de
migraciones para este proyecto.

El indice unico sobre sku es importante mas alla del rendimiento: convierte una
regla de negocio ("no puede haber dos productos con el mismo codigo") en una
garantia de la base de datos, que se cumple aunque dos peticiones simultaneas
intenten crear el mismo producto.
"""

import logging

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import ORDERS_COLLECTION, PRODUCTS_COLLECTION

logger = logging.getLogger(__name__)


async def create_indexes(database: AsyncIOMotorDatabase) -> None:
    """Crea los indices de productos y pedidos."""
    products = database[PRODUCTS_COLLECTION]
    await products.create_index("sku", unique=True, name="uq_product_sku")
    await products.create_index("category", name="ix_product_category")
    await products.create_index("is_active", name="ix_product_is_active")
    await products.create_index([("created_at", -1)], name="ix_product_created_at")

    orders = database[ORDERS_COLLECTION]
    await orders.create_index("order_number", unique=True, name="uq_order_number")
    await orders.create_index("customer.username", name="ix_order_customer")
    await orders.create_index("status", name="ix_order_status")
    await orders.create_index([("created_at", -1)], name="ix_order_created_at")

    logger.info("Indices verificados en las colecciones '%s' y '%s'", PRODUCTS_COLLECTION, ORDERS_COLLECTION)
