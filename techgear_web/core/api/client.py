"""Cliente HTTP hacia la API de TechGear.

ESTE es el unico modulo del portal que usa la libreria `requests`. La
integracion backend-frontend que pide el enunciado de la clase vive aqui.

Se centraliza en un solo lugar, en vez de repetir `requests.get(...)` en cada
vista, por cuatro razones concretas:

1. Una unica `Session` reutiliza la conexion TCP/TLS entre peticiones.
2. El `timeout` se aplica siempre. Una peticion sin timeout puede dejar colgada
   la vista de Django indefinidamente si la API no responde.
3. Los reintentos ante fallos transitorios se configuran una vez.
4. Los codigos de error HTTP se traducen a excepciones tipadas en un solo sitio,
   de modo que las vistas manejan errores de negocio y no codigos numericos.

Es el patron Gateway (o capa anticorrupcion): el resto del portal depende de
esta interfaz, no de los detalles de la API.
"""

import logging
from typing import Any

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.api.exceptions import APIError, APINotFound, APIUnavailable, APIValidationError

logger = logging.getLogger(__name__)


class TechGearAPIClient:
    """Envoltura de `requests` para hablar con el microservicio FastAPI."""

    def __init__(self, base_url: str | None = None, timeout: int | None = None) -> None:
        self.base_url = (base_url or settings.TECHGEAR_API_BASE_URL).rstrip('/')
        self.timeout = timeout or settings.TECHGEAR_API_TIMEOUT
        self.session = self._build_session()

    @staticmethod
    def _build_session() -> requests.Session:
        """Crea la sesion con politica de reintentos.

        Solo se reintentan metodos idempotentes: repetir un POST podria crear
        dos pedidos. El backoff exponencial evita golpear un servicio que ya
        esta en problemas.
        """
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=(502, 503, 504),
            allowed_methods=frozenset({'GET', 'HEAD', 'OPTIONS'}),
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Peticion GET a la API."""
        return self._request('GET', path, params=params)

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        """Peticion POST a la API."""
        return self._request('POST', path, json=payload)

    def patch(self, path: str, payload: dict[str, Any]) -> Any:
        """Peticion PATCH a la API."""
        return self._request('PATCH', path, json=payload)

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Ejecuta la peticion y traduce el resultado.

        Los parametros con valor None se descartan para no enviar
        `?category=None` a la API.
        """
        url = f"{self.base_url}/{path.lstrip('/')}"

        if 'params' in kwargs and kwargs['params']:
            kwargs['params'] = {clave: valor for clave, valor in kwargs['params'].items() if valor not in (None, '')}

        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.Timeout as error:
            logger.error('Timeout de %ss al llamar a %s', self.timeout, url)
            raise APIUnavailable(f'La API no respondio en {self.timeout} segundos.') from error
        except requests.ConnectionError as error:
            logger.error('No se pudo conectar con la API en %s', url)
            raise APIUnavailable('No se pudo establecer conexion con la API.') from error
        except requests.RequestException as error:
            logger.exception('Error inesperado al llamar a %s', url)
            raise APIError(str(error)) from error

        return self._handle_response(response)

    @staticmethod
    def _handle_response(response: requests.Response) -> Any:
        """Convierte la respuesta HTTP en datos o en una excepcion tipada."""
        if response.status_code == 204:
            return None

        if response.ok:
            return response.json()

        # La API responde los errores con el formato {"detail": ..., "code": ...}
        try:
            cuerpo = response.json()
        except ValueError:
            cuerpo = {}
        detalle = cuerpo.get('detail') if isinstance(cuerpo, dict) else None

        if response.status_code == 404:
            raise APINotFound(detalle or '', response.status_code)
        if response.status_code in (400, 409, 422):
            raise APIValidationError(detalle or '', response.status_code, errors=cuerpo)
        if response.status_code >= 500:
            logger.error('La API devolvio %s en %s', response.status_code, response.url)
            raise APIUnavailable(detalle or '', response.status_code)

        raise APIError(detalle or f'La API respondio con el codigo {response.status_code}.', response.status_code)


_client: TechGearAPIClient | None = None


def get_client() -> TechGearAPIClient:
    """Devuelve el cliente compartido, creandolo la primera vez.

    Se construye de forma perezosa y no al importar el modulo: asi lee la
    configuracion cuando Django ya termino de cargarla, y las pruebas pueden
    sustituirlo con reset_client() sin efectos entre casos.
    """
    global _client
    if _client is None:
        _client = TechGearAPIClient()
    return _client


def reset_client() -> None:
    """Descarta el cliente compartido. Util entre pruebas."""
    global _client
    _client = None
