"""Recurso Pedido de la API.

Se implementa en la Clase 4, junto con el carrito en sesion y el checkout.
La Clase 3 se limita al consumo del catalogo, que es lo que pide el enunciado.

Operaciones previstas:
- create_order(payload)          -> POST   /orders
- list_orders(customer=..., ...) -> GET    /orders
- get_order(order_id)            -> GET    /orders/{id}
"""
