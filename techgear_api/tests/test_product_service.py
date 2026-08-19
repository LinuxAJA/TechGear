"""Pruebas de las reglas de negocio del catalogo de productos."""

from decimal import Decimal

import pytest

from app.core.exceptions import DuplicateSkuError, ProductNotFoundError
from app.schemas.product import Category, ProductUpdate
from app.services.product_service import ProductService
from tests.conftest import build_product, seed_product


async def test_crear_producto_asigna_valores_controlados_por_el_servidor(
    product_service: ProductService,
) -> None:
    """El cliente no puede fijar is_active ni las marcas de tiempo."""
    product = await seed_product(product_service)

    assert product["is_active"] is True
    assert product["created_at"] == product["updated_at"]
    assert product["stock"] == 10


async def test_crear_producto_rechaza_sku_duplicado(product_service: ProductService) -> None:
    """El SKU es la clave de negocio y no puede repetirse."""
    await seed_product(product_service, sku="GPU-DUPLICADO")

    with pytest.raises(DuplicateSkuError) as error:
        await seed_product(product_service, sku="GPU-DUPLICADO")

    assert "GPU-DUPLICADO" in error.value.message


async def test_actualizar_producto_solo_modifica_lo_enviado(product_service: ProductService) -> None:
    """El comportamiento PATCH no debe borrar los campos omitidos."""
    product = await seed_product(product_service, name="Nombre original", price="1000.00")

    updated = await product_service.update_product(
        product["_id"], ProductUpdate(price=Decimal("2500.00"))
    )

    assert updated["price"] == Decimal("2500.00")
    assert updated["name"] == "Nombre original"
    assert updated["stock"] == product["stock"]


async def test_actualizar_producto_inexistente_falla(product_service: ProductService) -> None:
    """Un identificador desconocido produce un error de dominio, no un 500."""
    with pytest.raises(ProductNotFoundError):
        await product_service.update_product("66c1f3a2e8b1a2d4f0c9e123", ProductUpdate(stock=5))


async def test_desactivar_producto_lo_saca_del_catalogo(product_service: ProductService) -> None:
    """El borrado es logico: el documento se conserva pero deja de listarse."""
    product = await seed_product(product_service)

    await product_service.deactivate_product(product["_id"])

    activos, total_activos = await product_service.list_products(only_active=True)
    assert total_activos == 0
    assert activos == []

    # El documento sigue existiendo y es consultable por su identificador.
    conservado = await product_service.get_product(product["_id"])
    assert conservado["is_active"] is False


async def test_listar_productos_filtra_por_busqueda_y_categoria(
    product_service: ProductService,
) -> None:
    """La busqueda por texto parcial y el filtro por categoria funcionan."""
    await product_service.create_product(build_product(sku="GPU-01", name="RTX 4070", category=Category.GPU))
    await product_service.create_product(
        build_product(sku="CPU-01", name="Ryzen 7 5800X", category=Category.CPU)
    )

    # Busqueda parcial e insensible a mayusculas.
    encontrados, total = await product_service.list_products(search="rtx")
    assert total == 1
    assert encontrados[0]["sku"] == "GPU-01"

    # Filtro por categoria.
    cpus, total_cpus = await product_service.list_products(category=Category.CPU.value)
    assert total_cpus == 1
    assert cpus[0]["sku"] == "CPU-01"
