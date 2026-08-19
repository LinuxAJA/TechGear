"""Excepciones de dominio.

Estas excepciones describen que salio mal en terminos del NEGOCIO, no del
protocolo HTTP. Los servicios lanzan ProductNotFoundError, nunca HTTPException:
asi la logica de negocio no depende de FastAPI y puede reutilizarse desde un
script de carga, una tarea programada o una prueba unitaria.

La traduccion a codigos HTTP ocurre en un unico lugar: app/core/handlers.py.
"""


class DomainError(Exception):
    """Error de negocio. Se traduce a HTTP 400 por defecto."""

    code = "domain_error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(DomainError):
    """El recurso solicitado no existe. Se traduce a HTTP 404."""

    code = "not_found"


class ConflictError(DomainError):
    """La operacion choca con el estado actual de los datos. HTTP 409."""

    code = "conflict"


# ── Productos ─────────────────────────────────────────────
class ProductNotFoundError(NotFoundError):
    """No existe el producto solicitado."""

    code = "product_not_found"

    def __init__(self, product_id: str) -> None:
        super().__init__(f"No existe un producto con el identificador '{product_id}'.")


class DuplicateSkuError(ConflictError):
    """Ya hay un producto registrado con ese SKU."""

    code = "duplicate_sku"

    def __init__(self, sku: str) -> None:
        super().__init__(f"Ya existe un producto con el SKU '{sku}'.")


class InactiveProductError(ConflictError):
    """El producto existe pero fue retirado del catalogo."""

    code = "inactive_product"

    def __init__(self, name: str) -> None:
        super().__init__(f"El producto '{name}' no esta disponible para la venta.")


class InsufficientStockError(ConflictError):
    """No hay unidades suficientes para atender el pedido."""

    code = "insufficient_stock"

    def __init__(self, name: str, available: int, requested: int) -> None:
        self.available = available
        self.requested = requested
        super().__init__(
            f"Stock insuficiente para '{name}': se solicitaron {requested} "
            f"unidades y solo hay {available} disponibles."
        )


# ── Pedidos ───────────────────────────────────────────────
class OrderNotFoundError(NotFoundError):
    """No existe el pedido solicitado."""

    code = "order_not_found"

    def __init__(self, order_id: str) -> None:
        super().__init__(f"No existe un pedido con el identificador '{order_id}'.")


class InvalidStatusTransitionError(ConflictError):
    """El cambio de estado solicitado no esta permitido."""

    code = "invalid_status_transition"

    def __init__(self, current: str, requested: str) -> None:
        super().__init__(f"No se puede pasar un pedido de '{current}' a '{requested}'.")


class DuplicateOrderNumberError(ConflictError):
    """Colision al generar el numero de pedido.

    Es un error interno y transitorio: el servicio reintenta con un numero
    nuevo antes de dejar que llegue al cliente.
    """

    code = "duplicate_order_number"

    def __init__(self, order_number: str) -> None:
        super().__init__(f"Ya existe un pedido con el numero '{order_number}'.")
