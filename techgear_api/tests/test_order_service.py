"""Pruebas de las reglas de negocio del registro de pedidos.

Cada prueba corresponde a una decision de diseno documentada: el precio lo pone
el servidor, las lineas guardan un snapshot, el inventario se descuenta de forma
segura y un fallo parcial no deja stock bloqueado.
"""

from decimal import Decimal

import pytest

from app.core.exceptions import (
    InactiveProductError,
    InsufficientStockError,
    InvalidStatusTransitionError,
    OrderNotFoundError,
)
from app.schemas.order import OrderStatus
from app.schemas.product import ProductUpdate
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from tests.conftest import build_order, seed_product


async def test_el_total_lo_calcula_el_servidor(
    order_service: OrderService, product_service: ProductService
) -> None:
    """El cliente solo envia cantidades: precios, subtotales y total son del servidor."""
    product = await seed_product(product_service, price="3299900.00", stock=10)

    order = await order_service.create_order(build_order([(product["_id"], 2)]))

    assert order["items"][0]["unit_price"] == Decimal("3299900.00")
    assert order["items"][0]["subtotal"] == Decimal("6599800.00")
    assert order["total"] == Decimal("6599800.00")
    assert order["status"] == OrderStatus.PENDING
    assert order["order_number"].startswith("TG-")


async def test_la_linea_guarda_una_copia_del_precio(
    order_service: OrderService, product_service: ProductService
) -> None:
    """Cambiar el precio del producto no altera un pedido ya registrado."""
    product = await seed_product(product_service, price="1000.00", stock=10)
    order = await order_service.create_order(build_order([(product["_id"], 3)]))

    await product_service.update_product(product["_id"], ProductUpdate(price=Decimal("9999.00")))

    conservado = await order_service.get_order(order["_id"])
    assert conservado["items"][0]["unit_price"] == Decimal("1000.00")
    assert conservado["total"] == Decimal("3000.00")


async def test_crear_pedido_descuenta_el_inventario(
    order_service: OrderService, product_service: ProductService
) -> None:
    """El stock baja exactamente las unidades pedidas."""
    product = await seed_product(product_service, stock=10)

    await order_service.create_order(build_order([(product["_id"], 4)]))

    actualizado = await product_service.get_product(product["_id"])
    assert actualizado["stock"] == 6


async def test_stock_insuficiente_no_modifica_el_inventario(
    order_service: OrderService, product_service: ProductService
) -> None:
    """Si el pedido no se puede atender, nada queda descontado."""
    product = await seed_product(product_service, stock=2)

    with pytest.raises(InsufficientStockError) as error:
        await order_service.create_order(build_order([(product["_id"], 5)]))

    assert error.value.available == 2
    assert error.value.requested == 5

    intacto = await product_service.get_product(product["_id"])
    assert intacto["stock"] == 2


async def test_fallo_parcial_repone_lo_ya_descontado(
    order_service: OrderService, product_service: ProductService
) -> None:
    """Transaccion compensatoria: el primer producto debe recuperar su stock."""
    disponible = await seed_product(product_service, sku="GPU-OK", stock=10)
    agotado = await seed_product(product_service, sku="CPU-SIN-STOCK", stock=1)

    with pytest.raises(InsufficientStockError):
        await order_service.create_order(
            build_order([(disponible["_id"], 3), (agotado["_id"], 5)])
        )

    # El descuento del primer producto se revirtio.
    assert (await product_service.get_product(disponible["_id"]))["stock"] == 10
    assert (await product_service.get_product(agotado["_id"]))["stock"] == 1


async def test_lineas_repetidas_se_consolidan(
    order_service: OrderService, product_service: ProductService
) -> None:
    """El mismo producto en dos lineas produce una sola linea con la suma."""
    product = await seed_product(product_service, price="500.00", stock=10)

    order = await order_service.create_order(
        build_order([(product["_id"], 2), (product["_id"], 3)])
    )

    assert len(order["items"]) == 1
    assert order["items"][0]["quantity"] == 5
    assert order["total"] == Decimal("2500.00")
    assert (await product_service.get_product(product["_id"]))["stock"] == 5


async def test_no_se_puede_pedir_un_producto_retirado(
    order_service: OrderService, product_service: ProductService
) -> None:
    """Un producto con borrado logico no se puede comprar."""
    product = await seed_product(product_service, stock=10)
    await product_service.deactivate_product(product["_id"])

    with pytest.raises(InactiveProductError):
        await order_service.create_order(build_order([(product["_id"], 1)]))


async def test_pedido_inexistente_falla(order_service: OrderService) -> None:
    """Consultar un pedido que no existe produce un error de dominio."""
    with pytest.raises(OrderNotFoundError):
        await order_service.get_order("66c1f4b7e8b1a2d4f0c9e456")


async def test_transicion_de_estado_invalida(
    order_service: OrderService, product_service: ProductService
) -> None:
    """Un pedido pendiente no puede pasar directamente a entregado."""
    product = await seed_product(product_service, stock=10)
    order = await order_service.create_order(build_order([(product["_id"], 1)]))

    with pytest.raises(InvalidStatusTransitionError):
        await order_service.update_status(order["_id"], OrderStatus.DELIVERED)


async def test_transicion_de_estado_valida(
    order_service: OrderService, product_service: ProductService
) -> None:
    """La secuencia pendiente -> pagado -> enviado -> entregado si es valida."""
    product = await seed_product(product_service, stock=10)
    order = await order_service.create_order(build_order([(product["_id"], 1)]))

    for estado in (OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DELIVERED):
        actualizado = await order_service.update_status(order["_id"], estado)
        assert actualizado["status"] == estado


async def test_cancelar_un_pedido_repone_el_inventario(
    order_service: OrderService, product_service: ProductService
) -> None:
    """Las unidades reservadas vuelven a estar disponibles para la venta."""
    product = await seed_product(product_service, stock=10)
    order = await order_service.create_order(build_order([(product["_id"], 4)]))
    assert (await product_service.get_product(product["_id"]))["stock"] == 6

    await order_service.update_status(order["_id"], OrderStatus.CANCELLED)

    assert (await product_service.get_product(product["_id"]))["stock"] == 10


async def test_listar_pedidos_filtra_por_comprador(
    order_service: OrderService, product_service: ProductService
) -> None:
    """El filtro por username es lo que alimenta la vista 'Mis pedidos'."""
    product = await seed_product(product_service, stock=10)
    await order_service.create_order(build_order([(product["_id"], 1)], username="lino.aguirre"))
    await order_service.create_order(build_order([(product["_id"], 1)], username="otra.persona"))

    pedidos, total = await order_service.list_orders(customer="lino.aguirre")

    assert total == 1
    assert pedidos[0]["customer"]["username"] == "lino.aguirre"
