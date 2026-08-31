"""Modelos de pedidos.

Este archivo esta VACIO a proposito, igual que apps/catalog/models.py: los
pedidos se registran y consultan en la API (MongoDB), no en una tabla local.

El unico estado que SI vive en el portal es el carrito de compras, y
deliberadamente no es un modelo de base de datos: es estado del usuario
mientras compra, no un dato de negocio, y vive en la sesion
(ver apps/orders/cart.py). Nunca guarda precios, solo product_id y quantity.
"""
