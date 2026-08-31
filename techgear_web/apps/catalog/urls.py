"""Rutas del catalogo."""

from django.urls import path

from apps.catalog.views import (
    ProductCreateView,
    ProductDeleteView,
    ProductDetailView,
    ProductListView,
    ProductManageListView,
    ProductUpdateView,
)

app_name = 'catalog'

urlpatterns = [
    path('', ProductListView.as_view(), name='product_list'),
    path('producto/<str:product_id>/', ProductDetailView.as_view(), name='product_detail'),
    # Gestion (solo staff)
    path('gestion/productos/', ProductManageListView.as_view(), name='manage_product_list'),
    path('gestion/productos/nuevo/', ProductCreateView.as_view(), name='manage_product_create'),
    path('gestion/productos/<str:product_id>/editar/', ProductUpdateView.as_view(), name='manage_product_update'),
    path('gestion/productos/<str:product_id>/eliminar/', ProductDeleteView.as_view(), name='manage_product_delete'),
]
