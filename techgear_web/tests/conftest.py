"""Fixtures compartidas de la suite del portal.

Ninguna prueba de aqui levanta techgear_api: se usa `requests-mock` para
simular sus respuestas. Es la forma de cumplir el requisito de la Clase 6
("la suite debe pasar con FastAPI apagado") sin depender de que el backend
este corriendo ni de la base de datos real de MongoDB.
"""

from typing import Any

import pytest

from core.api.client import reset_client

API_BASE_URL = 'http://testserver-api/api/v1'


@pytest.fixture(autouse=True)
def _api_settings(settings):
    """Apunta el cliente HTTP a una URL falsa y limpia el cliente compartido.

    `get_client()` cachea una unica instancia de TechGearAPIClient a nivel de
    modulo (ver core/api/client.py). Sin resetearla entre pruebas, la
    PRIMERA prueba que se ejecute fijaria el base_url para todas las demas,
    sin importar lo que cada una configure despues.
    """
    settings.TECHGEAR_API_BASE_URL = API_BASE_URL
    settings.TECHGEAR_API_TIMEOUT = 5
    settings.TECHGEAR_API_RETRIES = 0  # las pruebas no deben esperar reintentos
    settings.TECHGEAR_API_BACKOFF = 0
    reset_client()
    yield
    reset_client()


def make_product(**overrides: Any) -> dict[str, Any]:
    """Documento de producto con la forma exacta de ProductPublic."""
    product = {
        'id': '66c1f3a2e8b1a2d4f0c9e123',
        'sku': 'GPU-RTX4070-01',
        'name': 'Tarjeta grafica NVIDIA RTX 4070 12GB',
        'description': 'GPU de gama alta con 12GB GDDR6X.',
        'category': 'gpu',
        'price': '3299900.00',
        'stock': 10,
        'image_url': None,
        'is_active': True,
        'created_at': '2026-08-01T10:00:00Z',
        'updated_at': '2026-08-01T10:00:00Z',
    }
    product.update(overrides)
    return product


def make_order(**overrides: Any) -> dict[str, Any]:
    """Documento de pedido con la forma exacta de OrderPublic."""
    order = {
        'id': '66c1f4b7e8b1a2d4f0c9e456',
        'order_number': 'TG-20260901-A3F2',
        'customer': {
            'username': 'lino.aguirre',
            'full_name': 'Lino Andres Aguirre',
            'email': 'lino@example.com',
            'phone': '3001234567',
            'address': 'Calle 10 # 20-30',
            'city': 'Medellin',
        },
        'items': [
            {
                'product_id': '66c1f3a2e8b1a2d4f0c9e123',
                'sku': 'GPU-RTX4070-01',
                'name': 'Tarjeta grafica NVIDIA RTX 4070 12GB',
                'unit_price': '3299900.00',
                'quantity': 1,
                'subtotal': '3299900.00',
            }
        ],
        'total': '3299900.00',
        'status': 'pending',
        'notes': '',
        'created_at': '2026-09-01T10:00:00Z',
        'updated_at': '2026-09-01T10:00:00Z',
    }
    order.update(overrides)
    return order


def page(items: list[dict[str, Any]], *, skip: int = 0, limit: int = 12) -> dict[str, Any]:
    """Sobre de paginacion identico al que devuelve la API."""
    return {'items': items, 'total': len(items), 'skip': skip, 'limit': limit}


def api_error(detail: str, code: str) -> dict[str, str]:
    """Cuerpo de error identico al que devuelve ErrorResponse en la API."""
    return {'detail': detail, 'code': code}


@pytest.fixture
def user(django_user_model):
    """Un usuario normal, sin privilegios de staff."""
    return django_user_model.objects.create_user(
        username='lino.aguirre', email='lino@example.com', password='clave-segura-123'
    )


@pytest.fixture
def staff_user(django_user_model):
    """Un usuario con is_staff=True, habilitado para la gestion de productos."""
    return django_user_model.objects.create_user(
        username='admin.tienda', email='admin@example.com', password='clave-segura-123', is_staff=True
    )


@pytest.fixture
def logged_in_client(client, user):
    """Cliente de pruebas ya autenticado como `user`."""
    client.force_login(user)
    return client


@pytest.fixture
def staff_client(client, staff_user):
    """Cliente de pruebas ya autenticado como un usuario staff."""
    client.force_login(staff_user)
    return client
