"""Pruebas del carrito en sesion.

El carrito no requiere sesion iniciada: cualquier visitante puede armar un
carrito, solo el checkout exige login (ver test_accounts.py).
"""

import pytest
from django.urls import reverse

from tests.conftest import API_BASE_URL, make_product

pytestmark = pytest.mark.django_db

PRODUCT_ID = '66c1f3a2e8b1a2d4f0c9e123'


def test_add_to_cart_then_view_shows_the_product(client, requests_mock):
    requests_mock.get(f'{API_BASE_URL}/products/{PRODUCT_ID}', json=make_product(id=PRODUCT_ID, stock=10))

    client.post(reverse('orders:cart_add', args=[PRODUCT_ID]), {'quantity': 2})
    response = client.get(reverse('orders:cart'))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'Tarjeta grafica NVIDIA RTX 4070 12GB' in content
    # 2 unidades a $3.299.900 = $6.599.800
    assert '6.599.800' in content


def test_adding_the_same_product_twice_consolidates_quantity(client, requests_mock):
    requests_mock.get(f'{API_BASE_URL}/products/{PRODUCT_ID}', json=make_product(id=PRODUCT_ID, stock=10))

    client.post(reverse('orders:cart_add', args=[PRODUCT_ID]), {'quantity': 2})
    client.post(reverse('orders:cart_add', args=[PRODUCT_ID]), {'quantity': 3})
    response = client.get(reverse('orders:cart'))

    assert 'value="5"' in response.content.decode()  # el input de cantidad muestra 5, no dos lineas


def test_cart_clamps_quantity_to_available_stock(client, requests_mock):
    # Se piden 20 unidades de un producto que solo tiene 4 en inventario.
    requests_mock.get(f'{API_BASE_URL}/products/{PRODUCT_ID}', json=make_product(id=PRODUCT_ID, stock=4))

    client.post(reverse('orders:cart_add', args=[PRODUCT_ID]), {'quantity': 20})
    response = client.get(reverse('orders:cart'))

    content = response.content.decode()
    assert 'value="4"' in content
    assert 'Cantidad ajustada' in content


def test_removing_a_retired_product_shows_a_warning(client, requests_mock):
    # El producto fue retirado del catalogo (is_active=False) mientras estaba
    # en el carrito: resolve_cart_lines debe quitarlo y avisar, no crashear.
    requests_mock.get(
        f'{API_BASE_URL}/products/{PRODUCT_ID}', json=make_product(id=PRODUCT_ID, is_active=False)
    )

    client.post(reverse('orders:cart_add', args=[PRODUCT_ID]), {'quantity': 1})
    response = client.get(reverse('orders:cart'))

    assert response.status_code == 200
    assert 'ya no estan disponibles' in response.content.decode()
    assert 'tu carrito esta vacio' in response.content.decode().lower()
