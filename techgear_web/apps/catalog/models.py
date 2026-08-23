"""Modelos del catalogo.

Este archivo esta VACIO a proposito y no es un descuido.

En esta arquitectura hibrida el modelo de dominio es remoto: los productos
viven en MongoDB Atlas y se consultan a traves de la API de FastAPI. El portal
Django no replica esos datos ni define un ORM para ellos, porque tener dos
fuentes de verdad para el mismo dato es justo lo que se quiere evitar.

La base SQLite del portal existe unicamente para django.contrib.auth: usuarios
y sesiones, que si son responsabilidad del frontend.
"""
