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

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        logger.warning("Error de dominio no clasificado en %s: %s", request.url.path, exc.message)
        return _build_response(status.HTTP_400_BAD_REQUEST, exc)
