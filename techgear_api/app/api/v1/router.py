"""Agregador de los routers de la version 1 de la API.

Tener un unico punto de montaje permite versionar el contrato: cuando exista
una v2, ambas versiones podran convivir sin romper al portal Django.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import orders, products

api_router = APIRouter()

api_router.include_router(products.router)
api_router.include_router(orders.router)
