"""Pruebas de 'Mis pedidos': la API no valida propiedad, Django si debe hacerlo.

GET /orders/{id} en la API devuelve cualquier pedido a quien conozca su
identificador. Estas pruebas verifican que el portal cierra ese hueco.
"""

import pytest
from django.urls import reverse

from tests.conftest import API_BASE_URL, make_order

pytestmark = pytest.mark.django_db

ORDER_ID = '66c1f4b7e8b1a2d4f0c9e456'


def test_user_can_view_their_own_order(logged_in_client, requests_mock):
    order = make_order(id=ORDER_ID)
    order['customer']['username'] = 'lino.aguirre'  # coincide con el fixture `user`
    requests_mock.get(f'{API_BASE_URL}/orders/{ORDER_ID}', json=order)

    response = logged_in_client.get(reverse('orders:order_detail', args=[ORDER_ID]))

    assert response.status_code == 200
    assert order['order_number'] in response.content.decode()


def test_user_cannot_view_someone_elses_order(logged_in_client, requests_mock):
    order = make_order(id=ORDER_ID)
    order['customer']['username'] = 'otra.persona'  # NO coincide con `user`
    requests_mock.get(f'{API_BASE_URL}/orders/{ORDER_ID}', json=order)

    response = logged_in_client.get(reverse('orders:order_detail', args=[ORDER_ID]))

    # Se responde 404, exactamente igual que un pedido inexistente: no debe
    # ser posible distinguir "no existe" de "existe pero no es tuyo".
    assert response.status_code == 404


def test_order_list_requires_login(client):
    response = client.get(reverse('orders:order_list'))

    assert response.status_code == 302
    assert reverse('accounts:login') in response.url


def test_cancel_someone_elses_order_returns_404(logged_in_client, requests_mock):
    order = make_order(id=ORDER_ID)
    order['customer']['username'] = 'otra.persona'
    requests_mock.get(f'{API_BASE_URL}/orders/{ORDER_ID}', json=order)

    response = logged_in_client.post(reverse('orders:order_cancel', args=[ORDER_ID]))

    assert response.status_code == 404
