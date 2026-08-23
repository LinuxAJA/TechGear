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

    Lanza APINotFound si no existe. Se usa a partir de la Clase 4, en la vista
    de detalle y al armar el carrito.
    """
    return get_client().get(f'/products/{product_id}')
