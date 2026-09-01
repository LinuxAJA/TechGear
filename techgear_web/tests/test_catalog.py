"""Pruebas del catalogo: listado, detalle y resiliencia ante la API caida.

Ninguna de estas pruebas necesita techgear_api arriba: requests_mock
intercepta cada llamada de `requests` antes de que salga a la red.
"""

import pytest
import requests
from django.urls import reverse

from tests.conftest import API_BASE_URL, api_error, make_product, page

# Toda vista toca request.session (backend por defecto: base de datos), asi
# que cada prueba de este modulo necesita acceso a la base de datos de prueba.
pytestmark = pytest.mark.django_db


def test_product_list_renders_products_from_the_api(client, requests_mock):
    producto = make_product(name='RTX 4070 de prueba')
    requests_mock.get(f'{API_BASE_URL}/products', json=page([producto]))

    response = client.get(reverse('catalog:product_list'))

    assert response.status_code == 200
    assert 'RTX 4070 de prueba' in response.content.decode()


def test_product_list_shows_service_unavailable_when_api_is_down(client, requests_mock):
    requests_mock.get(f'{API_BASE_URL}/products', exc=requests.ConnectionError)

    response = client.get(reverse('catalog:product_list'))

    # 503, no un 500: la vista debe reconocer que es un fallo de
    # infraestructura y mostrar la pagina de servicio no disponible.
    assert response.status_code == 503
    assert 'no esta disponible' in response.content.decode()


def test_product_detail_renders_a_single_product(client, requests_mock):
    producto = make_product(id='66c1f3a2e8b1a2d4f0c9e123', name='Producto de detalle')
    requests_mock.get(f'{API_BASE_URL}/products/66c1f3a2e8b1a2d4f0c9e123', json=producto)

    response = client.get(reverse('catalog:product_detail', args=['66c1f3a2e8b1a2d4f0c9e123']))

    assert response.status_code == 200
    assert 'Producto de detalle' in response.content.decode()


def test_product_detail_returns_404_for_unknown_id(client, requests_mock):
    requests_mock.get(
        f'{API_BASE_URL}/products/000000000000000000000000',
        status_code=404,
        json=api_error("No existe un producto con el identificador '...'.", 'product_not_found'),
    )

    response = client.get(reverse('catalog:product_detail', args=['000000000000000000000000']))

    # APINotFound se traduce a Http404, no a la pagina de servicio caido.
    assert response.status_code == 404
