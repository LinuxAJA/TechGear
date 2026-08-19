"""Esquemas Pydantic del Producto.

Se define un esquema distinto por cada direccion del dato (entrada de creacion,
entrada de actualizacion, documento interno y salida publica). Un unico modelo
para todo obligaria a marcar como opcionales campos que si son obligatorios al
crear, y expondria hacia afuera campos que son internos.
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, HttpUrl

from app.schemas.common import PyObjectId


class Category(StrEnum):
    """Categorias de hardware que maneja TechGear.

    Se modela como enumeracion y no como texto libre: Swagger lo muestra como
    una lista desplegable, Pydantic rechaza valores invalidos y el portal
    Django construye el filtro del catalogo a partir de estos mismos valores.
    """

    CPU = "cpu"
    GPU = "gpu"
    RAM = "ram"
    STORAGE = "storage"
    PERIPHERAL = "peripheral"
    ACCESSORY = "accessory"


class ProductBase(BaseModel):
    """Campos comunes a la creacion y a la salida de un producto."""

    model_config = ConfigDict(str_strip_whitespace=True)

    sku: str = Field(
        description="Codigo unico de inventario. Es la clave de negocio del producto",
        pattern=r"^[A-Z0-9\-]{4,20}$",
        examples=["GPU-RTX4070-01"],
    )
    name: str = Field(
        description="Nombre comercial del producto",
        min_length=3,
        max_length=120,
        examples=["Tarjeta grafica NVIDIA RTX 4070 12GB"],
    )
    description: str = Field(
        default="",
        description="Descripcion detallada del producto",
        max_length=1000,
        examples=["GPU de gama alta con 12GB GDDR6X, ideal para juegos en 1440p."],
    )
    category: Category = Field(
        description="Categoria a la que pertenece el producto",
        examples=[Category.GPU],
    )
    # Se usa Decimal y no float: los flotantes binarios no representan valores
    # monetarios de forma exacta y el error se acumula al sumar los totales de
    # un pedido. En JSON, Pydantic serializa Decimal como cadena ("1299.99"),
    # que es exactamente lo que conserva la precision.
    price: Decimal = Field(
        description="Precio unitario en pesos colombianos",
        gt=0,
        max_digits=12,
        decimal_places=2,
        examples=["3299900.00"],
    )
    stock: int = Field(
        description="Unidades disponibles en inventario",
        ge=0,
        examples=[15],
    )
    image_url: HttpUrl | None = Field(
        default=None,
        description="URL de la imagen del producto",
        examples=["https://example.com/rtx4070.jpg"],
    )


class ProductCreate(ProductBase):
    """Cuerpo del POST /products.

    Hereda de ProductBase sin agregar nada: el cliente no puede enviar id,
    is_active ni las marcas de tiempo, porque esos campos los controla el
    servidor.
    """


class ProductUpdate(BaseModel):
    """Cuerpo del PATCH /products/{id}.

    Todos los campos son opcionales y en el servicio se aplica
    model_dump(exclude_unset=True), de modo que los campos no enviados
    conservan su valor en vez de sobrescribirse con null.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=3, max_length=120, description="Nuevo nombre")
    description: str | None = Field(default=None, max_length=1000, description="Nueva descripcion")
    category: Category | None = Field(default=None, description="Nueva categoria")
    price: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2, description="Nuevo precio unitario"
    )
    stock: int | None = Field(default=None, ge=0, description="Nuevo nivel de inventario")
    image_url: HttpUrl | None = Field(default=None, description="Nueva URL de imagen")
    is_active: bool | None = Field(default=None, description="Activa o desactiva el producto en el catalogo")


class ProductPublic(ProductBase):
    """Respuesta de la API para un producto.

    El campo id se lee tanto de "_id" (como viene de MongoDB) como de "id",
    pero siempre se serializa como "id". Se usa validation_alias en lugar de
    alias porque FastAPI serializa las respuestas con by_alias=True: con un
    alias normal, la API expondria "_id" hacia afuera.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId = Field(
        validation_alias=AliasChoices("_id", "id"),
        description="Identificador unico del producto",
        examples=["66c1f3a2e8b1a2d4f0c9e123"],
    )
    is_active: bool = Field(description="Indica si el producto se muestra en el catalogo", examples=[True])
    created_at: datetime = Field(description="Fecha de creacion (UTC)")
    updated_at: datetime = Field(description="Fecha de la ultima modificacion (UTC)")
