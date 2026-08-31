"""Carrito de compras en sesion.

El carrito NUNCA guarda precios: solo `product_id` y `quantity`. Los precios
se releen de la API cada vez que se muestra el carrito, y el total definitivo
lo calcula el servidor al registrar el pedido (POST /orders). Si el carrito
guardara el precio, cualquiera podria manipularlo desde las herramientas de
desarrollador del navegador antes de pagar; es la misma regla de negocio que
protege el registro de pedidos en la API (ver app/services/order_service.py).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterator

from django.http import HttpRequest

from core.api import products as products_api
from core.api.exceptions import APINotFound

SESSION_KEY = 'cart'

# Limite razonable por linea, alineado con OrderItemCreate.quantity (le=100)
# en la API: no tiene sentido dejar que el carrito acumule mas de lo que la
# API aceptaria de todas formas.
MAX_QUANTITY_PER_ITEM = 100


class Cart:
    """Envoltorio de `request.session` para las operaciones del carrito."""

    def __init__(self, request: HttpRequest) -> None:
        self.session = request.session
        cart = self.session.get(SESSION_KEY)
        if cart is None:
            cart = self.session[SESSION_KEY] = {}
        self._items: dict[str, int] = cart

    def add(self, product_id: str, quantity: int = 1) -> None:
        """Agrega unidades de un producto. Si ya estaba, suma a lo existente."""
        nueva_cantidad = self._items.get(product_id, 0) + max(quantity, 1)
        self._items[product_id] = min(nueva_cantidad, MAX_QUANTITY_PER_ITEM)
        self._save()

    def set_quantity(self, product_id: str, quantity: int) -> None:
        """Fija la cantidad exacta de un producto. Cero o menos lo elimina."""
        if quantity <= 0:
            self.remove(product_id)
            return
        self._items[product_id] = min(quantity, MAX_QUANTITY_PER_ITEM)
        self._save()

    def remove(self, product_id: str) -> None:
        """Quita un producto del carrito."""
        if product_id in self._items:
            del self._items[product_id]
            self._save()

    def clear(self) -> None:
        """Vacia el carrito por completo (tras un checkout exitoso)."""
        self._items = {}
        self._save()

    def _save(self) -> None:
        self.session[SESSION_KEY] = self._items
        self.session.modified = True

    def __iter__(self) -> Iterator[tuple[str, int]]:
        return iter(self._items.items())

    def __len__(self) -> int:
        """Cantidad TOTAL de unidades, para el contador de la navbar."""
        return sum(self._items.values())

    @property
    def is_empty(self) -> bool:
        return not self._items


@dataclass
class CartLine:
    """Una linea del carrito ya resuelta contra la API, lista para mostrar."""

    product: dict[str, Any]
    quantity: int
    subtotal: Decimal
    quantity_adjusted: bool = False


def resolve_cart_lines(cart: Cart) -> tuple[list[CartLine], list[str]]:
    """Convierte los (product_id, quantity) del carrito en lineas mostrables.

    Hace lo que el carrito, por diseño, no puede hacer solo: consultar el
    precio y el stock ACTUALES de cada producto. Tres casos se resuelven aqui
    y no al llegar al checkout, para que el usuario los vea antes de pagar:

    - El producto ya no existe (fue borrado): se quita del carrito.
    - El producto fue retirado del catalogo o se agoto: se quita del carrito.
    - Hay menos stock que lo pedido: la cantidad se reduce al maximo posible
      y la linea se marca como `quantity_adjusted` para avisar en la plantilla.

    Devuelve (lineas, ids_retirados) y deja el carrito ya limpio de los
    productos que ya no se pueden comprar.
    """
    lineas: list[CartLine] = []
    retirados: list[str] = []

    for product_id, quantity in list(cart):
        try:
            product = products_api.get_product(product_id)
        except APINotFound:
            retirados.append(product_id)
            cart.remove(product_id)
            continue

        if not product.get('is_active', True) or product.get('stock', 0) <= 0:
            retirados.append(product_id)
            cart.remove(product_id)
            continue

        ajustada = False
        if quantity > product['stock']:
            quantity = product['stock']
            cart.set_quantity(product_id, quantity)
            ajustada = True

        precio_unitario = Decimal(str(product['price']))
        lineas.append(
            CartLine(
                product=product,
                quantity=quantity,
                subtotal=precio_unitario * quantity,
                quantity_adjusted=ajustada,
            )
        )

    return lineas, retirados
