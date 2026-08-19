"""Punto de entrada de la API de TechGear.

Este modulo solo compone la aplicacion: crea la instancia de FastAPI, configura
el ciclo de vida y monta los routers. No contiene reglas de negocio ni accesos
a la base de datos; esas responsabilidades viven en app/services y
app/repositories respectivamente.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import health
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.handlers import register_exception_handlers
from app.db.indexes import create_indexes
from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_database

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el arranque y el apagado de la aplicacion.

    Al arrancar abre la conexion con MongoDB Atlas, verifica con un ping que
    responda y asegura los indices de las colecciones. Al apagar cierra el
    cliente para liberar las conexiones del pool.
    """
    await connect_to_mongo()
    await create_indexes(get_database())
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.app_name,
    description=(
        "Microservicio de catalogo y pedidos de TechGear.\n\n"
        "Administra el inventario de hardware y el registro de pedidos sobre "
        "MongoDB Atlas. Es consumido por el portal web construido en Django."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Traduce las excepciones de dominio a respuestas HTTP uniformes.
register_exception_handlers(app)

# CORS: el portal Django llama a esta API desde el servidor, asi que hoy no lo
# necesita. Se deja configurado para cuando existan clientes que corran en el
# navegador (por ejemplo, filtros del catalogo con JavaScript).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sonda de infraestructura, fuera del prefijo de version.
app.include_router(health.router)

# Contrato de negocio, versionado.
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["Estado del servicio"], summary="Mensaje de bienvenida")
async def root() -> dict[str, str]:
    """Punto de entrada informativo de la API."""
    return {
        "message": f"Bienvenido a {settings.app_name}.",
        "documentacion": "/docs",
        "estado": "/health",
    }
