"""Mixins de vista reutilizables entre apps.

Vive en core/ y no en una app de dominio especifica porque tanto catalog como
orders necesitan la misma traduccion de errores de la API a paginas HTML.
"""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render

from core.api.exceptions import APIError, APIUnavailable

logger = logging.getLogger(__name__)


class APIErrorHandlingMixin:
    """Convierte los fallos de la API en paginas utiles.

    Que la API no responda no es un error del programa: es un estado esperado
    del sistema, y el usuario debe ver una pagina que lo explique en vez de una
    traza. Se captura alrededor de get_context_data porque es ahi donde ocurren
    las llamadas HTTP.

    Los errores mas especificos (APINotFound -> Http404, APIValidationError ->
    error de formulario) se manejan dentro de cada vista, ANTES de que lleguen
    aqui: este mixin es la red de seguridad para lo que queda, que en la
    practica es casi siempre APIUnavailable.
    """

    def get(self, request, *args, **kwargs):
        try:
            context = self.get_context_data(**kwargs)
        except APIUnavailable as error:
            # Subclase de APIError: debe ir primero o nunca se alcanzaria.
            logger.warning('API no disponible en %s: %s', request.path, error.detail)
            return render(request, 'errors/api_unavailable.html', {'detail': error.detail}, status=503)
        except APIError as error:
            logger.error('Error de la API en %s: %s', request.path, error.detail)
            return render(request, 'errors/api_unavailable.html', {'detail': error.detail}, status=502)

        return self.render_to_response(context)


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restringe una vista a usuarios con `is_staff=True`.

    Un usuario anonimo se redirige al login (comportamiento de
    LoginRequiredMixin); uno autenticado pero sin permisos recibe un 403
    (comportamiento de UserPassesTestMixin). El orden de la herencia importa:
    LoginRequiredMixin debe ir primero para que su dispatch() se ejecute antes.

    ADVERTENCIA DE DISEÑO, no un descuido: esto es una barrera de INTERFAZ, no
    de seguridad real. La API de FastAPI no tiene autenticacion propia, asi
    que cualquiera que conozca su URL puede llamar a POST /products
    directamente sin pasar por este mixin. La solucion correcta seria una
    clave de servicio o JWT en la API; queda anotada como evolucion futura.
    """

    def test_func(self) -> bool:
        return bool(self.request.user.is_staff)
