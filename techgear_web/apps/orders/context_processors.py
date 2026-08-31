"""Context processor del carrito.

Inyecta el contador de unidades en TODAS las plantillas, para que la navbar
pueda mostrarlo sin que cada vista tenga que pasarlo explicitamente en su
contexto.
"""

from django.http import HttpRequest

from apps.orders.cart import Cart


def cart(request: HttpRequest) -> dict[str, int]:
    """Expone `cart_items_count` en el contexto de cada plantilla."""
    return {'cart_items_count': len(Cart(request))}
