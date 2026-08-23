"""Excepciones del cliente de la API.

Las vistas nunca ven un objeto Response de requests ni un codigo HTTP suelto:
ven una de estas excepciones. Asi, si manana cambia la forma en que la API
reporta un error, se ajusta el cliente y no cada vista del portal.
"""


class APIError(Exception):
    """Error generico al comunicarse con la API de TechGear."""

    mensaje_usuario = 'Ocurrio un problema al comunicarse con el servicio de TechGear.'

    def __init__(self, detail: str = '', status_code: int | None = None) -> None:
        self.detail = detail or self.mensaje_usuario
        self.status_code = status_code
        super().__init__(self.detail)


class APINotFound(APIError):
    """La API respondio 404: el recurso solicitado no existe."""

    mensaje_usuario = 'El recurso solicitado no existe.'


class APIValidationError(APIError):
    """La API respondio 422 o 409: los datos enviados no son validos.

    Conserva el detalle que devuelve la API para poder mostrarlo en el
    formulario correspondiente en lugar de un mensaje generico.
    """

    mensaje_usuario = 'Los datos enviados no son validos.'

    def __init__(self, detail: str = '', status_code: int | None = None, errors: object = None) -> None:
        super().__init__(detail, status_code)
        self.errors = errors


class APIUnavailable(APIError):
    """La API no responde: esta apagada, hubo timeout o devolvio un 5xx.

    Es la unica que representa un fallo de infraestructura y no del usuario;
    las vistas la traducen a una pagina de servicio no disponible.
    """

    mensaje_usuario = (
        'El servicio de catalogo no esta disponible en este momento. '
        'Intentalo de nuevo en unos minutos.'
    )
