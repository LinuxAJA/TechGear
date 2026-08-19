"""Conversion entre tipos de Python y tipos de BSON.

Todo el conocimiento sobre como MongoDB representa los datos vive aqui y en los
repositorios que usan estas funciones. Ni los servicios ni los endpoints saben
que existe Decimal128.
"""

from decimal import Decimal
from enum import Enum
from typing import Any

from bson import Decimal128, ObjectId
from bson.errors import InvalidId
from pydantic import AnyUrl


def to_mongo(value: Any) -> Any:
    """Convierte una estructura de Python a tipos que BSON entiende.

    Recorre diccionarios y listas de forma recursiva porque los pedidos llevan
    lineas anidadas con precios dentro.

    - Decimal  -> Decimal128, para conservar la precision exacta del dinero.
      Guardar un precio como float haria que 0.1 + 0.2 no fuera 0.3.
    - Enum     -> su valor primitivo, para no depender de la clase de Python.
    - AnyUrl   -> texto, porque BSON no conoce los tipos de URL de Pydantic.
    """
    if isinstance(value, Decimal):
        return Decimal128(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, AnyUrl):
        return str(value)
    if isinstance(value, dict):
        return {key: to_mongo(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_mongo(item) for item in value]
    return value


def from_mongo(value: Any) -> Any:
    """Convierte un documento de MongoDB a tipos de Python.

    Solo necesita deshacer Decimal128; el ObjectId del _id lo transforma
    Pydantic mediante el tipo PyObjectId al construir el esquema de salida.
    """
    if isinstance(value, Decimal128):
        return value.to_decimal()
    if isinstance(value, dict):
        return {key: from_mongo(item) for key, item in value.items()}
    if isinstance(value, list):
        return [from_mongo(item) for item in value]
    return value


def to_object_id(value: str) -> ObjectId | None:
    """Convierte texto a ObjectId, o None si el formato es invalido.

    Devolver None en vez de propagar InvalidId permite que el repositorio
    trate un identificador mal formado igual que uno inexistente, y que el
    servicio responda 404 en lugar de un error 500.
    """
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None
