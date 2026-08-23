"""Rutas del catalogo."""

from django.urls import path

from apps.catalog.views import ProductListView

app_name = 'catalog'

urlpatterns = [
    path('', ProductListView.as_view(), name='product_list'),
]
