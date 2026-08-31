"""Recurso Producto de la API.

Traduce las operaciones del catalogo a llamadas concretas del cliente HTTP.
Las vistas llaman a estas funciones y reciben diccionarios; no conocen rutas,
ni parametros de consulta, ni codigos de estado.
"""

from typing import Any

from core.api.client import get_client

# Tamano de pagina del catalogo. La API acepta hasta 100.
PAGE_SIZE = 12


def list_products(
    *,
    page: int = 1,
    search: str | None = None,
    category: str | None = None,
    page_size: int = PAGE_SIZE,
) -> dict[str, Any]:
    """Consulta el catalogo y devuelve el sobre de paginacion de la API.

    La API pagina con `skip`/`limit`, pero en la interfaz web es mas natural
    hablar de numeros de pagina. La conversion se hace aqui, en un solo lugar.

    Devuelve un diccionario con `items`, `total`, `skip` y `limit`.
    """
    page = max(page, 1)
    return get_client().get(
        '/products',
        params={
            'skip': (page - 1) * page_size,
            'limit': page_size,
            'q': search,
            'category': category,
        },
    )


def get_product(product_id: str) -> dict[str, Any]:
    """Consulta un producto por su identificador.

    Lanza APINotFound si no existe. Se usa en la vista de detalle y al armar
    el carrito.
    """
    return get_client().get(f'/products/{product_id}')


def list_products_for_management() -> dict[str, Any]:
    """Lista TODOS los productos, incluidos los retirados del catalogo.

    Se usa solo en la seccion de gestion (Clase 5): el listado publico filtra
    is_active=True por defecto y ahi no serviria para ver, ni reactivar, un
    producto que ya fue dado de baja.
    """
    return get_client().get('/products', params={'limit': 100, 'only_active': False})


def create_product(data: dict[str, Any]) -> dict[str, Any]:
    """Crea un producto. Lanza APIValidationError (409) si el SKU ya existe."""
    return get_client().post('/products', data)


def update_product(product_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    """Actualiza parcialmente un producto.

    `changes` debe llevar solo los campos que realmente cambiaron: la API
    aplica exclude_unset=True, asi que enviar un campo con su mismo valor no
    tiene efecto, pero enviar de mas puede pisar cambios concurrentes.
    """
    return get_client().patch(f'/products/{product_id}', changes)


def delete_product(product_id: str) -> None:
    """Retira un producto del catalogo (borrado logico en la API)."""
    get_client().delete(f'/products/{product_id}')
