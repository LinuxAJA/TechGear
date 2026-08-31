"""Rutas de carrito, checkout e historial de pedidos."""

from django.urls import path

from apps.orders.views import (
    CartAddView,
    CartRemoveView,
    CartView,
    CheckoutView,
    OrderCancelView,
    OrderDetailView,
    OrderListView,
)

app_name = 'orders'

urlpatterns = [
    path('carrito/', CartView.as_view(), name='cart'),
    path('carrito/agregar/<str:product_id>/', CartAddView.as_view(), name='cart_add'),
    path('carrito/eliminar/<str:product_id>/', CartRemoveView.as_view(), name='cart_remove'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('mis-pedidos/', OrderListView.as_view(), name='order_list'),
    path('mis-pedidos/<str:order_id>/', OrderDetailView.as_view(), name='order_detail'),
    path('mis-pedidos/<str:order_id>/cancelar/', OrderCancelView.as_view(), name='order_cancel'),
]
