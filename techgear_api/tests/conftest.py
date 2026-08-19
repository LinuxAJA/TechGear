"""Fixtures compartidas por la suite de pruebas."""

from decimal import Decimal
from typing import Any

import pytest

from app.schemas.order import CustomerInfo, OrderCreate, OrderItemCreate
from app.schemas.product import Category, ProductCreate
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from tests.fakes import InMemoryOrderRepository, InMemoryProductRepository


@pytest.fixture
def product_repository() -> InMemoryProductRepository:
    """Repositorio de productos en memoria."""
    return InMemoryProductRepository()


@pytest.fixture
def order_repository() -> InMemoryOrderRepository:
    """Repositorio de pedidos en memoria."""
    return InMemoryOrderRepository()


@pytest.fixture
def product_service(product_repository: InMemoryProductRepository) -> ProductService:
    """Servicio de productos apoyado en el repositorio falso."""
    return ProductService(product_repository)  # type: ignore[arg-type]


@pytest.fixture
def order_service(
    order_repository: InMemoryOrderRepository,
    product_repository: InMemoryProductRepository,
) -> OrderService:
    """Servicio de pedidos apoyado en los repositorios falsos."""
    return OrderService(order_repository, product_repository)  # type: ignore[arg-type]


def build_product(
    *,
    sku: str = "GPU-RTX4070-01",
    name: str = "Tarjeta grafica RTX 4070",
    category: Category = Category.GPU,
    price: str = "3299900.00",
    stock: int = 10,
) -> ProductCreate:
    """Arma un esquema de creacion de producto con valores por defecto."""
    return ProductCreate(
        sku=sku,
        name=name,
        description="Producto de prueba",
        category=category,
        price=Decimal(price),
        stock=stock,
    )


def build_order(items: list[tuple[str, int]], *, username: str = "lino.aguirre") -> OrderCreate:
    """Arma un esquema de creacion de pedido a partir de (product_id, cantidad)."""
    return OrderCreate(
        customer=CustomerInfo(
            username=username,
            full_name="Lino Andres Aguirre",
            email="lino@example.com",
            phone="3001234567",
            address="Calle 10 # 20-30",
            city="Medellin",
        ),
        items=[OrderItemCreate(product_id=product_id, quantity=quantity) for product_id, quantity in items],
    )


async def seed_product(service: ProductService, **kwargs: Any) -> dict[str, Any]:
    """Crea un producto de prueba y devuelve el documento resultante."""
    return await service.create_product(build_product(**kwargs))
