"""Esquemas y tipos compartidos por todo el dominio."""

from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, BeforeValidator, Field

# ──────────────────────────────────────────────────────────
# Identificadores de MongoDB
# ──────────────────────────────────────────────────────────
# El _id de MongoDB es un ObjectId, un tipo de BSON que no es serializable a
# JSON y que Pydantic no conoce. BeforeValidator(str) lo convierte a texto en
# el borde del sistema, de modo que hacia afuera la API siempre expone cadenas.
PyObjectId = Annotated[str, BeforeValidator(str)]

# Patron de un ObjectId valido: 24 caracteres hexadecimales.
# Se usa para rechazar identificadores mal formados antes de tocar la base.
OBJECT_ID_PATTERN = r"^[0-9a-fA-F]{24}$"


# ──────────────────────────────────────────────────────────
# Respuestas genericas
# ──────────────────────────────────────────────────────────
T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Sobre de paginacion.

    Ningun listado de la API devuelve una coleccion sin limite: siempre viaja
    envuelto aqui, para que el cliente sepa cuantos elementos hay en total y
    pueda pedir la siguiente pagina.
    """

    items: list[T] = Field(description="Elementos de la pagina actual")
    total: int = Field(description="Cantidad total de elementos que cumplen el filtro", examples=[42])
    skip: int = Field(description="Cantidad de elementos omitidos", examples=[0])
    limit: int = Field(description="Tamano maximo de la pagina", examples=[20])


class MessageResponse(BaseModel):
    """Respuesta simple con un mensaje informativo."""

    message: str = Field(description="Mensaje para el cliente")


class ErrorResponse(BaseModel):
    """Formato uniforme de error de toda la API.

    Que todos los errores tengan la misma forma permite que el portal Django
    los interprete con un solo bloque de codigo.
    """

    detail: str = Field(description="Descripcion del error", examples=["El producto no existe"])
    code: str | None = Field(default=None, description="Codigo interno del error", examples=["product_not_found"])


class HealthResponse(BaseModel):
    """Estado del servicio y de su conexion a la base de datos."""

    status: str = Field(description="Estado general del servicio", examples=["ok"])
    database: str = Field(description="Estado de la conexion a MongoDB", examples=["connected"])
    version: str = Field(description="Version de la API", examples=["1.0.0"])
