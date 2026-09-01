"""Pruebas de la gestion de productos (staff): el CRUD ejercitado desde el
frontend contra POST, PATCH y DELETE de la API."""

from django.urls import reverse

import pytest

from tests.conftest import API_BASE_URL, api_error, make_product

pytestmark = pytest.mark.django_db

PRODUCT_ID = '66c1f3a2e8b1a2d4f0c9e123'

VALID_PRODUCT_DATA = {
    'sku': 'SSD-NVME-1TB',
    'name': 'SSD NVMe 1TB',
    'description': 'Unidad de estado solido',
    'category': 'storage',
    'price': '450000.00',
    'stock': '20',
    'image_url': '',
}


def test_create_product_success(staff_client, requests_mock):
    requests_mock.post(f'{API_BASE_URL}/products', json=make_product(sku='SSD-NVME-1TB'), status_code=201)

    response = staff_client.post(reverse('catalog:manage_product_create'), VALID_PRODUCT_DATA)

    assert response.status_code == 302
    assert response.url == reverse('catalog:manage_product_list')


def test_create_product_duplicate_sku_shows_error_on_sku_field(staff_client, requests_mock):
    requests_mock.post(
        f'{API_BASE_URL}/products',
        status_code=409,
        json=api_error("Ya existe un producto con el SKU 'SSD-NVME-1TB'.", 'duplicate_sku'),
    )

    response = staff_client.post(reverse('catalog:manage_product_create'), VALID_PRODUCT_DATA)

    assert response.status_code == 200
    content = response.content.decode()
    assert 'Ya existe un producto con el SKU' in content
    # El error debe quedar anclado al campo sku (aria-describedby="id_sku_error"),
    # no como un error generico del formulario.
    assert 'id_sku_error' in content


def test_update_product_success(staff_client, requests_mock):
    requests_mock.get(f'{API_BASE_URL}/products/{PRODUCT_ID}', json=make_product(id=PRODUCT_ID))
    requests_mock.patch(f'{API_BASE_URL}/products/{PRODUCT_ID}', json=make_product(id=PRODUCT_ID, price='399000.00'))

    response = staff_client.post(
        reverse('catalog:manage_product_update', args=[PRODUCT_ID]),
        {
            'name': 'Nombre actualizado',
            'description': '',
            'category': 'gpu',
            'price': '399000.00',
            'stock': '5',
            'image_url': '',
            'is_active': 'on',
        },
    )

    assert response.status_code == 302
    enviado = requests_mock.last_request.json()
    assert enviado['price'] == '399000.00'
    assert 'sku' not in enviado  # el SKU no se puede editar


def test_delete_product_retires_it(staff_client, requests_mock):
    requests_mock.delete(f'{API_BASE_URL}/products/{PRODUCT_ID}', status_code=204)

    response = staff_client.post(reverse('catalog:manage_product_delete', args=[PRODUCT_ID]))

    assert response.status_code == 302
    assert response.url == reverse('catalog:manage_product_list')
