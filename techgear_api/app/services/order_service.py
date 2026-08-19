"""Reglas de negocio del Pedido.

Aqui viven las decisiones que protegen el negocio:

1. El precio NUNCA llega desde el cliente. Se lee del producto en la base de
   datos, porque aceptarlo del comprador permitiria fijar cualquier valor.
2. Cada linea guarda un snapshot del sku, el nombre y el precio del momento de
   la compra, para que un cambio de precio futuro no altere pedidos pasados.
3. El inventario se descuenta de forma atomica y condicional.
4. Si algo falla a mitad de camino, se reponen las unidades ya descontadas
   (transaccion compensatoria).
"""

import logging
import secrets
from decimal import Decimal
from typing import Any, NoReturn

from app.core.exceptions import (
    DuplicateOrderNumberError,
    InactiveProductError,
    InsufficientStockError,
    InvalidStatusTransitionError,
    OrderNotFoundError,
    ProductNotFoundError,
)
from app.core.utils import utcnow
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order import OrderCreate, OrderItemCreate, OrderStatus

logger = logging.getLogger(__name__)

# Transiciones de estado permitidas. Tenerlas en una tabla, y no repartidas en
# condicionales, hace que la regla se pueda leer de un vistazo y probar sola.
ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDING: frozenset({OrderStatus.PAID, OrderStatus.CANCELLED}),
    OrderStatus.PAID: frozenset({OrderStatus.SHIPPED, OrderStatus.CANCELLED}),
    OrderStatus.SHIPPED: frozenset({OrderStatus.DELIVERED}),
    OrderStatus.DELIVERED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}

# Intentos de generacion del numero de pedido ante una colision improbable.
ORDER_NUMBER_ATTEMPTS = 3


class OrderService:
    """Casos de uso del registro de pedidos."""

    def __init__(self, order_repository: OrderRepository, product_repository: ProductRepository) -> None:
        self._orders = order_repository
        self._products = product_repository

    # ── Casos de uso ──────────────────────────────────────
    async def create_order(self, payload: OrderCreate) -> dict[str, Any]:
        """Registra un pedido descontando el inventario."""
        now = utcnow()
        quantities = self._aggregate_quantities(payload.items)

        items, reserved = await self._reserve_stock(quantities, now)
        try:
            document = {
                "customer": payload.customer.model_dump(),
                "items": items,
                "total": sum((item["subtotal"] for item in items), Decimal("0")),
                "status": OrderStatus.PENDING,
                "notes": payload.notes,
                "created_at": now,
                "updated_at": now,
            }
            return await self._persist_with_unique_number(document)
        except Exception:
            # Si la insercion falla despues de haber descontado, hay que
            # reponer el inventario o quedaria bloqueado sin pedido asociado.
            await self._release_stock(reserved, now)
            raise

    async def get_order(self, order_id: str) -> dict[str, Any]:
        """Devuelve un pedido o falla si no existe."""
        order = await self._orders.get_by_id(order_id)
        if order is None:
            raise OrderNotFoundError(order_id)
        return order

    async def list_orders(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        customer: str | None = None,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Devuelve una pagina de pedidos."""
        return await self._orders.list_orders(skip=skip, limit=limit, customer=customer, status=status)

    async def update_status(self, order_id: str, new_status: OrderStatus) -> dict[str, Any]:
        """Cambia el estado de un pedido validando la transicion.

        Cancelar un pedido devuelve las unidades al inventario: las que estaban
        reservadas para ese pedido vuelven a estar disponibles para la venta.
        """
        order = await self.get_order(order_id)
        current_status = OrderStatus(order["status"])

        if new_status is current_status:
            return order

        if new_status not in ALLOWED_TRANSITIONS[current_status]:
            raise InvalidStatusTransitionError(current_status.value, new_status.value)

        now = utcnow()
        if new_status is OrderStatus.CANCELLED:
            reserved = [(item["product_id"], item["quantity"]) for item in order["items"]]
            await self._release_stock(reserved, now)

        updated = await self._orders.update_status(order_id, new_status.value, updated_at=now)
        if updated is None:
            raise OrderNotFoundError(order_id)
        return updated

    # ── Apoyo interno ─────────────────────────────────────
    @staticmethod
    def _aggregate_quantities(items: list[OrderItemCreate]) -> dict[str, int]:
        """Suma las cantidades por producto.

        Si el cliente envia el mismo producto en dos lineas, se consolidan en
        una sola: asi el pedido queda con una linea por producto y el descuento
        de inventario se hace en una unica operacion atomica.
        """
        quantities: dict[str, int] = {}
        for item in items:
            quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity
        return quantities

    async def _reserve_stock(
        self, quantities: dict[str, int], now: Any
    ) -> tuple[list[dict[str, Any]], list[tuple[str, int]]]:
        """Descuenta el inventario y arma las lineas del pedido.

        Devuelve las lineas ya calculadas y la lista de reservas aplicadas,
        que sirve para compensar si algo falla mas adelante.
        """
        items: list[dict[str, Any]] = []
        reserved: list[tuple[str, int]] = []

        try:
            for product_id, quantity in quantities.items():
                product = await self._products.decrement_stock(product_id, quantity, updated_at=now)
                if product is None:
                    await self._raise_reservation_error(product_id, quantity)

                reserved.append((product_id, quantity))
                unit_price: Decimal = product["price"]
                items.append(
                    {
                        "product_id": product_id,
                        "sku": product["sku"],
                        "name": product["name"],
                        "unit_price": unit_price,
                        "quantity": quantity,
                        "subtotal": unit_price * quantity,
                    }
                )
        except Exception:
            await self._release_stock(reserved, now)
            raise

        return items, reserved

    async def _raise_reservation_error(self, product_id: str, quantity: int) -> NoReturn:
        """Traduce un descuento fallido al error de negocio correspondiente.

        El descuento atomico devuelve None sin decir por que; se consulta el
        producto para saber si no existe, esta inactivo o no alcanza el stock.
        """
        product = await self._products.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        if not product.get("is_active", False):
            raise InactiveProductError(product["name"])
        raise InsufficientStockError(product["name"], available=product["stock"], requested=quantity)

    async def _release_stock(self, reserved: list[tuple[str, int]], now: Any) -> None:
        """Repone las unidades descontadas."""
        for product_id, quantity in reserved:
            await self._products.restore_stock(product_id, quantity, updated_at=now)

    async def _persist_with_unique_number(self, document: dict[str, Any]) -> dict[str, Any]:
        """Inserta el pedido reintentando si el numero generado ya existe."""
        for attempt in range(1, ORDER_NUMBER_ATTEMPTS + 1):
            document["order_number"] = self._generate_order_number()
            try:
                return await self._orders.create(document)
            except DuplicateOrderNumberError:
                logger.warning(
                    "Colision de numero de pedido en el intento %s de %s", attempt, ORDER_NUMBER_ATTEMPTS
                )
        raise DuplicateOrderNumberError(str(document.get("order_number")))

    @staticmethod
    def _generate_order_number() -> str:
        """Genera un numero legible del tipo TG-20260818-A3F2.

        Se muestra al usuario en lugar del _id de MongoDB, que es un detalle
        tecnico sin significado para el comprador.
        """
        return f"TG-{utcnow():%Y%m%d}-{secrets.token_hex(2).upper()}"
