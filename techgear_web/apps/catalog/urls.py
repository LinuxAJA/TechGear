"""Rutas del catalogo."""

from django.urls import path

from apps.catalog.views import ProductDetailView, ProductListView

app_name = 'catalog'

urlpatterns = [
    path('', ProductListView.as_view(), name='product_list'),
    path('producto/<str:product_id>/', ProductDetailView.as_view(), name='product_detail'),
]
