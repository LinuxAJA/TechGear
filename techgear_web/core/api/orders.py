"""Recurso Pedido de la API.

Traduce las operaciones de checkout, historial y cancelacion a llamadas
concretas del cliente HTTP. Ninguna vista arma el payload de OrderCreate a
mano: todas pasan por create_order().
"""

from typing import Any

from core.api.client import get_client


def create_order(*, customer: dict[str, Any], items: list[dict[str, Any]], notes: str = '') -> dict[str, Any]:
    """Registra un pedido.

    `items` es una lista de {'product_id': ..., 'quantity': ...}. El precio
    NUNCA viaja desde aqui: la API lo lee de la base de datos, calcula los
    subtotales y el total, y descuenta el inventario de forma atomica. Puede
    lanzar APIValidationError (404 producto inexistente, 409 sin stock o
    producto retirado) o APIUnavailable.
    """
    return get_client().post(
        '/orders',
        {'customer': customer, 'items': items, 'notes': notes},
    )


def list_orders(*, customer: str | None = None, status: str | None = None, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """Lista pedidos, tipicamente filtrados por el username del comprador.

    Se usa para construir "Mis pedidos": cada usuario solo debe ver los
    suyos, y el filtro `customer` es lo que lo garantiza.
    """
    page = max(page, 1)
    return get_client().get(
        '/orders',
        params={
            'skip': (page - 1) * page_size,
            'limit': page_size,
            'customer': customer,
            'status': status,
        },
    )


def get_order(order_id: str) -> dict[str, Any]:
    """Consulta un pedido por su identificador. Lanza APINotFound si no existe.

    OJO: la API no valida propiedad. Cualquier vista que use esta funcion para
    mostrar el pedido a un usuario debe comprobar, aparte, que
    order['customer']['username'] coincide con el usuario autenticado.
    """
    return get_client().get(f'/orders/{order_id}')


def update_order_status(order_id: str, status: str) -> dict[str, Any]:
    """Cambia el estado de un pedido (por ejemplo, para cancelarlo).

    Cancelar repone el inventario en la API. Lanza APIValidationError (409) si
    la transicion de estado no es valida.
    """
    return get_client().patch(f'/orders/{order_id}/status', {'status': status})
