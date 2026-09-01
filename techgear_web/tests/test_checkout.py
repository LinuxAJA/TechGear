"""Pruebas del flujo de checkout: la entrega central de la Clase 5.

Cubren exactamente los casos que pide la Clase 6: stock insuficiente
mostrado en el formulario, y la API caida sin perder el carrito.
"""

import pytest
import requests
from django.urls import reverse

from tests.conftest import API_BASE_URL, api_error, make_order, make_product

pytestmark = pytest.mark.django_db

PRODUCT_ID = '66c1f3a2e8b1a2d4f0c9e123'

VALID_CHECKOUT_DATA = {
    'full_name': 'Lino Andres Aguirre',
    'email': 'lino@example.com',
    'phone': '3001234567',
    'address': 'Calle 10 # 20-30',
    'city': 'Medellin',
    'notes': 'Entregar en la manana',
}


def _add_product_to_cart(client, requests_mock, **product_overrides):
    requests_mock.get(f'{API_BASE_URL}/products/{PRODUCT_ID}', json=make_product(id=PRODUCT_ID, **product_overrides))
    client.post(reverse('orders:cart_add', args=[PRODUCT_ID]), {'quantity': 1})


def test_checkout_get_redirects_when_cart_is_empty(logged_in_client):
    response = logged_in_client.get(reverse('orders:checkout'))

    assert response.status_code == 302
    assert response.url == reverse('catalog:product_list')


def test_checkout_success_creates_order_and_clears_cart(logged_in_client, requests_mock):
    _add_product_to_cart(logged_in_client, requests_mock)
    order = make_order(id='66c1f4b7e8b1a2d4f0c9e456', order_number='TG-20260901-A3F2')
    requests_mock.post(f'{API_BASE_URL}/orders', json=order, status_code=201)

    response = logged_in_client.post(reverse('orders:checkout'), VALID_CHECKOUT_DATA)

    assert response.status_code == 302
    assert response.url == reverse('orders:order_detail', args=['66c1f4b7e8b1a2d4f0c9e456'])

    # El precio jamas viajo desde el cliente: solo product_id y quantity.
    enviado = requests_mock.last_request.json()
    assert enviado['items'] == [{'product_id': PRODUCT_ID, 'quantity': 1}]
    assert 'price' not in enviado['items'][0]

    # El carrito quedo vacio tras el pedido exitoso.
    cart_response = logged_in_client.get(reverse('orders:cart'))
    assert 'tu carrito esta vacio' in cart_response.content.decode().lower()


def test_checkout_insufficient_stock_shows_error_on_the_form(logged_in_client, requests_mock):
    _add_product_to_cart(logged_in_client, requests_mock, stock=50)  # pasa la validacion local del carrito
    requests_mock.post(
        f'{API_BASE_URL}/orders',
        status_code=409,
        json=api_error(
            "Stock insuficiente para 'Tarjeta grafica NVIDIA RTX 4070 12GB': "
            "se solicito 1 unidad y solo hay 0 disponibles.",
            'insufficient_stock',
        ),
    )

    response = logged_in_client.post(reverse('orders:checkout'), VALID_CHECKOUT_DATA)

    assert response.status_code == 200  # se re-renderiza el formulario, no se redirige
    assert 'Stock insuficiente' in response.content.decode()

    # El carrito NO se vacio: el usuario debe poder ajustar y reintentar.
    cart_response = logged_in_client.get(reverse('orders:cart'))
    assert 'tu carrito esta vacio' not in cart_response.content.decode().lower()


def test_checkout_keeps_cart_when_api_is_unavailable(logged_in_client, requests_mock):
    _add_product_to_cart(logged_in_client, requests_mock)
    requests_mock.post(f'{API_BASE_URL}/orders', exc=requests.ConnectionError)

    response = logged_in_client.post(reverse('orders:checkout'), VALID_CHECKOUT_DATA)

    # Un POST no se reintenta solo: se informa el fallo sin perder el carrito.
    assert response.status_code == 200
    assert 'no esta disponible' in response.content.decode() or 'no se pudo' in response.content.decode().lower()

    cart_response = logged_in_client.get(reverse('orders:cart'))
    assert 'tu carrito esta vacio' not in cart_response.content.decode().lower()


def test_checkout_get_shows_service_unavailable_when_api_is_down(logged_in_client, requests_mock):
    requests_mock.get(f'{API_BASE_URL}/products/{PRODUCT_ID}', exc=requests.ConnectionError)

    # OJO: `client.session` es una property que devuelve una instancia NUEVA
    # en cada acceso; hay que capturarla en una variable antes de mutarla, o
    # la asignacion se pierde silenciosamente sobre un objeto descartado.
    session = logged_in_client.session
    session['cart'] = {PRODUCT_ID: 1}
    session.save()

    response = logged_in_client.get(reverse('orders:checkout'))

    assert response.status_code == 503
    assert 'no esta disponible' in response.content.decode()
