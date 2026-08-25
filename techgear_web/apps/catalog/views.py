"""Vistas del catalogo.

Consumen el catalogo de la API de TechGear y lo renderizan con el sistema de
plantillas de Django. Son la "V" y la "T" del patron MVT; la "M" es remota
(ver models.py).

Se usa TemplateView y no ListView/DetailView porque esas clases esperan un
QuerySet de la base de datos local, y aqui los productos llegan por HTTP.
"""

import logging

from django.http import Http404
from django.shortcuts import render
from django.views.generic import TemplateView

from apps.catalog.constants import CATEGORIES
from core.api import products as products_api
from core.api.exceptions import APIError, APINotFound, APIUnavailable

logger = logging.getLogger(__name__)


class APIErrorHandlingMixin:
    """Convierte los fallos de la API en paginas utiles.

    Que la API no responda no es un error del programa: es un estado esperado
    del sistema, y el usuario debe ver una pagina que lo explique en vez de una
    traza. Se captura alrededor de get_context_data porque es ahi donde ocurren
    las llamadas HTTP.
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


class ProductListView(APIErrorHandlingMixin, TemplateView):
    """Vista principal: listado paginado del catalogo."""

    template_name = 'catalog/product_list.html'

    def get_context_data(self, **kwargs):
        """Consulta la API y arma el contexto de la plantilla."""
        context = super().get_context_data(**kwargs)

        search = self.request.GET.get('q', '').strip()
        category = self.request.GET.get('category', '').strip()
        page = self._get_page_number()

        pagina = products_api.list_products(page=page, search=search or None, category=category or None)

        total = pagina['total']
        limit = pagina['limit'] or products_api.PAGE_SIZE
        total_paginas = max((total + limit - 1) // limit, 1)

        context.update(
            {
                'products': pagina['items'],
                'total': total,
                'page': page,
                'total_pages': total_paginas,
                'has_previous': page > 1,
                'has_next': page < total_paginas,
                'search': search,
                'selected_category': category,
                'categories': CATEGORIES,
            }
        )
        return context

    def _get_page_number(self) -> int:
        """Lee ?page= de forma tolerante: cualquier basura equivale a la pagina 1."""
        try:
            return max(int(self.request.GET.get('page', 1)), 1)
        except (TypeError, ValueError):
            return 1


class ProductDetailView(APIErrorHandlingMixin, TemplateView):
    """Ficha de un producto."""

    template_name = 'catalog/product_detail.html'

    def get_context_data(self, **kwargs):
        """Consulta un producto puntual de la API."""
        context = super().get_context_data(**kwargs)
        product_id = kwargs['product_id']

        try:
            product = products_api.get_product(product_id)
        except APINotFound as error:
            # Se traduce a Http404 para que Django use la pagina 404 del sitio.
            # Debe capturarse aqui: APINotFound es subclase de APIError y, de no
            # hacerlo, el mixin lo mostraria como un fallo del servicio.
            raise Http404('El producto solicitado no existe.') from error

        context['product'] = product
        return context
