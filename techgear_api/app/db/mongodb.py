"""Conexion a MongoDB Atlas.

Este modulo y el paquete app/repositories/ son los UNICOS lugares del proyecto
que conocen Motor, BSON y los detalles del almacenamiento. Las capas de
servicios y de endpoints trabajan con objetos Python puros.

Nota tecnica: Motor quedo deprecado en 2025 en favor del soporte asincrono
nativo de PyMongo (AsyncMongoClient). Se usa aqui por fidelidad con el ejemplo
visto en clase; al estar aislado en este archivo, migrar en el futuro consiste
en cambiar el import y el nombre del cliente.
"""

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Nombres de las colecciones. Centralizados para no repetir cadenas sueltas.
PRODUCTS_COLLECTION = "products"
ORDERS_COLLECTION = "orders"


class MongoDB:
    """Contenedor del cliente y la base de datos activos."""

    client: AsyncIOMotorClient | None = None
    database: AsyncIOMotorDatabase | None = None


mongodb = MongoDB()


async def connect_to_mongo() -> None:
    """Abre la conexion y verifica que Atlas responda.

    Se llama desde el lifespan de FastAPI. El ping inicial es intencional:
    es preferible fallar al arrancar que descubrir la caida en la primera
    peticion de un usuario.
    """
    settings = get_settings()

    mongodb.client = AsyncIOMotorClient(
        settings.mongodb_url,
        # Falla rapido si Atlas no responde, en vez de esperar 30 segundos.
        serverSelectionTimeoutMS=5000,
        # Devuelve datetimes con zona horaria (UTC) en lugar de datetimes naive.
        tz_aware=True,
    )
    mongodb.database = mongodb.client[settings.mongodb_db]

    await mongodb.client.admin.command("ping")
    logger.info("Conexion a MongoDB Atlas exitosa (base de datos: %s)", settings.mongodb_db)


async def close_mongo_connection() -> None:
    """Cierra la conexion al apagar la aplicacion."""
    if mongodb.client is not None:
        mongodb.client.close()
        mongodb.client = None
        mongodb.database = None
        logger.info("Conexion a MongoDB cerrada")


def get_database() -> AsyncIOMotorDatabase:
    """Devuelve la base de datos activa.

    Es la dependencia que usaran los repositorios. Lanza RuntimeError si se
    invoca antes de que el lifespan haya conectado, lo que convierte un error
    silencioso en uno explicito.
    """
    if mongodb.database is None:
        raise RuntimeError(
            "La base de datos no esta inicializada. "
            "Verifica que la aplicacion se haya arrancado a traves de su lifespan."
        )
    return mongodb.database
