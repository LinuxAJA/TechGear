"""Traduccion de excepciones de dominio a respuestas HTTP.

Este es el unico punto del proyecto donde el negocio se encuentra con el
protocolo. Gracias a esto, en los servicios no hay ni un solo
`raise HTTPException`, y todos los errores de la API salen con la misma forma
(ErrorResponse), lo que permite que el portal Django los interprete con un
unico bloque de codigo.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from app.core.exceptions import ConflictError, DomainError, NotFoundError
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)


def _build_response(status_code: int, error: DomainError) -> JSONResponse:
    """Arma la respuesta uniforme de error."""
    payload = ErrorResponse(detail=error.message, code=error.code)
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    """Registra los manejadores en la aplicacion.

    Starlette busca el manejador recorriendo la jerarquia de clases de la
    excepcion, asi que el mas especifico gana: ProductNotFoundError encuentra
    primero el manejador de NotFoundError y nunca llega al de DomainError.
    """

    @app.exception_handler(NotFoundError)
    async def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
        return _build_response(status.HTTP_404_NOT_FOUND, exc)

    @app.exception_handler(ConflictError)
    async def handle_conflict(request: Request, exc: ConflictError) -> JSONResponse:
        return _build_response(status.HTTP_409_CONFLICT, exc)


    @app.exception_handler(PyMongoError)
    async def handle_database_error(request: Request, exc: PyMongoError) -> JSONResponse:
        """Traduce los fallos de MongoDB a un 503 con el formato uniforme.

        Sin este manejador, un corte transitorio hacia Atlas (por ejemplo un
        ServerSelectionTimeoutError) sale como un 500 con traza. Son fallos de
        INFRAESTRUCTURA, no peticiones invalidas: 503 le dice al cliente que
        vuelva a intentarlo, y el portal Django ya sabe presentar ese caso.

        Se registra el detalle tecnico en el log, pero no se expone al cliente:
        el mensaje de pymongo incluye los nombres de host del cluster.
        """
        logger.error("Fallo de MongoDB en %s: %s", request.url.path, exc)
        payload = ErrorResponse(
            detail="La base de datos no esta disponible en este momento. Intentalo de nuevo.",
            code="database_unavailable",
        )
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload.model_dump())

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        logger.warning("Error de dominio no clasificado en %s: %s", request.url.path, exc.message)
        return _build_response(status.HTTP_400_BAD_REQUEST, exc)
