"""Agregador de los routers de la version 1 de la API.

Tener un unico punto de montaje permite versionar el contrato: cuando exista
una v2, ambas versiones podran convivir sin romper al portal Django.
"""

from fastapi import APIRouter

api_router = APIRouter()

# Los routers de productos y pedidos se montan aqui en la Clase 2:
# api_router.include_router(products.router)
# api_router.include_router(orders.router)
