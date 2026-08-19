"""Esquemas Pydantic del Pedido.

Aqui vive la decision de diseno mas importante del dominio: el cliente solo
envia que producto quiere y cuantas unidades. Nunca envia el precio. El
servidor lo lee de la base de datos, calcula los subtotales y el total, y
guarda una copia (snapshot) del nombre y el precio del momento de la compra.
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import OBJECT_ID_PATTERN, PyObjectId


class OrderStatus(StrEnum):
    """Estados por los que pasa un pedido."""

    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class CustomerInfo(BaseModel):
    """Datos de contacto y envio del comprador.

    El username proviene del usuario autenticado en Django; es lo que permite
    despues listar "mis pedidos" sin duplicar la tabla de usuarios en MongoDB.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(
        description="Nombre de usuario autenticado en el portal Django",
        min_length=3,
        max_length=150,
        examples=["lino.aguirre"],
    )
    full_name: str = Field(description="Nombre completo del comprador", min_length=3, max_length=120,
                           examples=["Lino Andres Aguirre"])
    email: EmailStr = Field(description="Correo de contacto", examples=["lino@example.com"])
    phone: str = Field(description="Telefono de contacto", pattern=r"^[0-9+\s\-]{7,20}$", examples=["3001234567"])
    address: str = Field(description="Direccion de entrega", min_length=5, max_length=200,
                         examples=["Calle 10 # 20-30, Apto 401"])
    city: str = Field(description="Ciudad de entrega", min_length=3, max_length=80, examples=["Medellin"])


class OrderItemCreate(BaseModel):
    """Linea de pedido tal como la envia el cliente.

    Solo identificador y cantidad: aceptar el precio desde el cliente permitiria
    comprar cualquier producto al valor que el comprador decida.
    """

    product_id: str = Field(
        description="Identificador del producto a comprar",
        pattern=OBJECT_ID_PATTERN,
        examples=["66c1f3a2e8b1a2d4f0c9e123"],
    )
    quantity: int = Field(description="Unidades solicitadas", ge=1, le=100, examples=[2])


class OrderCreate(BaseModel):
    """Cuerpo del POST /orders."""

    model_config = ConfigDict(str_strip_whitespace=True)

    customer: CustomerInfo = Field(description="Datos del comprador")
    items: list[OrderItemCreate] = Field(
        description="Lineas del pedido. Debe haber al menos una",
        min_length=1,
        max_length=50,
    )
    notes: str = Field(default="", description="Observaciones para el despacho", max_length=500)


class OrderItem(BaseModel):
    """Linea de pedido ya procesada y persistida.

    Guarda una copia del sku, el nombre y el precio unitario vigentes en el
    momento de la compra. Es denormalizacion intencional: si manana cambia el
    precio del producto, el total de un pedido de ayer no puede cambiar con el.
    """

    product_id: PyObjectId = Field(description="Identificador del producto comprado")
    sku: str = Field(description="SKU del producto al momento de la compra", examples=["GPU-RTX4070-01"])
    name: str = Field(description="Nombre del producto al momento de la compra")
    unit_price: Decimal = Field(description="Precio unitario congelado al momento de la compra",
                                examples=["3299900.00"])
    quantity: int = Field(description="Unidades compradas", ge=1, examples=[2])
    subtotal: Decimal = Field(description="unit_price multiplicado por quantity", examples=["6599800.00"])


class OrderPublic(BaseModel):
    """Respuesta de la API para un pedido."""

    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId = Field(
        validation_alias=AliasChoices("_id", "id"),
        description="Identificador unico del pedido",
        examples=["66c1f4b7e8b1a2d4f0c9e456"],
    )
    order_number: str = Field(
        description="Numero de pedido legible que se muestra al usuario",
        examples=["TG-20260818-A3F2"],
    )
    customer: CustomerInfo = Field(description="Datos del comprador")
    items: list[OrderItem] = Field(description="Lineas del pedido con precios congelados")
    total: Decimal = Field(description="Suma de todos los subtotales, calculada por el servidor",
                           examples=["6599800.00"])
    status: OrderStatus = Field(description="Estado actual del pedido", examples=[OrderStatus.PENDING])
    notes: str = Field(default="", description="Observaciones para el despacho")
    created_at: datetime = Field(description="Fecha de creacion (UTC)")
    updated_at: datetime = Field(description="Fecha de la ultima modificacion (UTC)")


class OrderStatusUpdate(BaseModel):
    """Cuerpo del PATCH /orders/{id}/status."""

    status: OrderStatus = Field(description="Nuevo estado del pedido", examples=[OrderStatus.PAID])
