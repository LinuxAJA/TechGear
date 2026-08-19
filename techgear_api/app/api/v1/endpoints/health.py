"""Endpoint de diagnostico del servicio.

Se expone fuera de /api/v1 a proposito: no es parte del contrato de negocio,
sino una sonda de infraestructura que debe seguir existiendo aunque la version
de la API cambie.
"""

import logging

from fastapi import APIRouter

from app.core.config import get_settings
from app.db.mongodb import mongodb
from app.schemas.common import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Estado del servicio"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Verificar el estado del servicio",
    description="Comprueba que la API responde y que la conexion con MongoDB Atlas sigue viva.",
)
async def health_check() -> HealthResponse:
    """Devuelve el estado de la API y de su base de datos."""
    settings = get_settings()
    database_status = "disconnected"

    if mongodb.client is not None:
        try:
            await mongodb.client.admin.command("ping")
            database_status = "connected"
        except Exception as error:  # noqa: BLE001 - la sonda nunca debe tumbar el servicio
            logger.warning("MongoDB no responde al ping: %s", error)
            database_status = "unreachable"

    return HealthResponse(
        status="ok" if database_status == "connected" else "degraded",
        database=database_status,
        version=settings.app_version,
    )
