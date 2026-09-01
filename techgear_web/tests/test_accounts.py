"""Pruebas de registro, autenticacion y control de acceso."""

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from tests.conftest import API_BASE_URL, page

pytestmark = pytest.mark.django_db


def test_register_creates_a_user_and_logs_in_automatically(client):
    response = client.post(
        reverse('accounts:register'),
        {
            'username': 'nuevo.usuario',
            'email': 'nuevo@example.com',
            'password1': 'ClaveSegura!2026',
            'password2': 'ClaveSegura!2026',
        },
    )

    assert response.status_code == 302
    assert User.objects.filter(username='nuevo.usuario').exists()
    # Auto-login: no deberia hacer falta un segundo POST a /cuenta/login/.
    assert '_auth_user_id' in client.session


def test_register_rejects_mismatched_passwords(client):
    response = client.post(
        reverse('accounts:register'),
        {
            'username': 'otro.usuario',
            'email': 'otro@example.com',
            'password1': 'ClaveSegura!2026',
            'password2': 'NoCoincide!2026',
        },
    )

    assert response.status_code == 200  # se re-renderiza el formulario con errores
    assert not User.objects.filter(username='otro.usuario').exists()


def test_checkout_redirects_anonymous_users_to_login(client):
    response = client.get(reverse('orders:checkout'))

    assert response.status_code == 302
    assert reverse('accounts:login') in response.url


def test_manage_products_redirects_anonymous_users_to_login(client):
    response = client.get(reverse('catalog:manage_product_list'))

    assert response.status_code == 302
    assert reverse('accounts:login') in response.url


def test_manage_products_forbidden_for_authenticated_non_staff(logged_in_client):
    response = logged_in_client.get(reverse('catalog:manage_product_list'))

    # Autenticado pero sin permisos: 403, no una redireccion a login.
    assert response.status_code == 403


def test_manage_products_allowed_for_staff(staff_client, requests_mock):
    requests_mock.get(f'{API_BASE_URL}/products', json=page([]))

    response = staff_client.get(reverse('catalog:manage_product_list'))

    assert response.status_code == 200
