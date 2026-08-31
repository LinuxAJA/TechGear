"""Vistas del catalogo.

Consumen el catalogo de la API de TechGear y lo renderizan con el sistema de
plantillas de Django. Son la "V" y la "T" del patron MVT; la "M" es remota
(ver models.py).

Se usa TemplateView y no ListView/DetailView porque esas clases esperan un
QuerySet de la base de datos local, y aqui los productos llegan por HTTP.
"""

import logging

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, TemplateView

from apps.catalog.constants import CATEGORIES
from apps.catalog.forms import ProductCreateForm, ProductUpdateForm
from core.api import products as products_api
from core.api.exceptions import APINotFound, APIUnavailable, APIValidationError
from core.mixins import APIErrorHandlingMixin, StaffRequiredMixin

logger = logging.getLogger(__name__)


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


# ── Gestion de productos (seccion staff) ──────────────────────────────────
# Ejercita los cuatro verbos del CRUD (POST, GET, PATCH, DELETE) desde el
# frontend contra los endpoints que la API ya expone desde la Clase 2. Ver la
# advertencia de diseno en StaffRequiredMixin: esto restringe la INTERFAZ, no
# la API en si, que no tiene autenticacion propia.


class ProductManageListView(StaffRequiredMixin, APIErrorHandlingMixin, TemplateView):
    """Listado de gestion: incluye tambien los productos retirados."""

    template_name = 'catalog/manage/product_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pagina = products_api.list_products_for_management()
        context['products'] = pagina['items']
        return context


class ProductCreateView(StaffRequiredMixin, FormView):
    """Alta de un producto nuevo. POST /products."""

    template_name = 'catalog/manage/product_form.html'
    form_class = ProductCreateForm
    success_url = reverse_lazy('catalog:manage_product_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modo'] = 'crear'
        return context

    def form_valid(self, form):
        payload = {
            'sku': form.cleaned_data['sku'],
            'name': form.cleaned_data['name'],
            'description': form.cleaned_data['description'],
            'category': form.cleaned_data['category'],
            'price': str(form.cleaned_data['price']),
            'stock': form.cleaned_data['stock'],
            'image_url': form.cleaned_data['image_url'] or None,
        }
        try:
            products_api.create_product(payload)
        except APIValidationError as error:
            # duplicate_sku es el unico 409 posible al crear: se ancla al
            # campo sku para que el usuario sepa exactamente que corregir.
            if error.errors and isinstance(error.errors, dict) and error.errors.get('code') == 'duplicate_sku':
                form.add_error('sku', error.detail)
            else:
                form.add_error(None, error.detail)
            return self.form_invalid(form)
        except APIUnavailable as error:
            messages.error(self.request, error.mensaje_usuario)
            return self.form_invalid(form)

        messages.success(self.request, f"Producto «{form.cleaned_data['name']}» creado correctamente.")
        return super().form_valid(form)


class ProductUpdateView(StaffRequiredMixin, FormView):
    """Edicion de un producto existente. PATCH /products/{id}.

    Solo viajan los campos del formulario: como todos tienen un valor inicial
    precargado desde la API, en la practica siempre se envian todos, pero eso
    es responsabilidad de ProductUpdate en la API (acepta un reemplazo total
    de los campos editables sin tocar el SKU ni las marcas de tiempo).
    """

    template_name = 'catalog/manage/product_form.html'
    form_class = ProductUpdateForm
    success_url = reverse_lazy('catalog:manage_product_list')

    def get_initial(self):
        # Se cachea en self.product porque get_context_data lo vuelve a usar.
        # Los mixins de autenticacion ya se ejecutaron antes de llegar aqui
        # (dispatch de StaffRequiredMixin), asi que este fetch nunca ocurre
        # para un usuario sin permisos.
        if not hasattr(self, 'product'):
            try:
                self.product = products_api.get_product(self.kwargs['product_id'])
            except APINotFound as error:
                raise Http404('El producto solicitado no existe.') from error

        product = self.product
        return {
            'name': product['name'],
            'description': product['description'],
            'category': product['category'],
            'price': product['price'],
            'stock': product['stock'],
            'image_url': product['image_url'] or '',
            'is_active': product['is_active'],
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modo'] = 'editar'
        context['product'] = self.product
        return context

    def form_valid(self, form):
        changes = {
            'name': form.cleaned_data['name'],
            'description': form.cleaned_data['description'],
            'category': form.cleaned_data['category'],
            'price': str(form.cleaned_data['price']),
            'stock': form.cleaned_data['stock'],
            'image_url': form.cleaned_data['image_url'] or None,
            'is_active': form.cleaned_data['is_active'],
        }
        try:
            products_api.update_product(self.kwargs['product_id'], changes)
        except APIValidationError as error:
            form.add_error(None, error.detail)
            return self.form_invalid(form)
        except APIUnavailable as error:
            messages.error(self.request, error.mensaje_usuario)
            return self.form_invalid(form)

        messages.success(self.request, f"Producto «{form.cleaned_data['name']}» actualizado correctamente.")
        return super().form_valid(form)


class ProductDeleteView(StaffRequiredMixin, View):
    """Retira un producto del catalogo. DELETE /products/{id} (borrado logico).

    Solo acepta POST: un DELETE accesible por GET se podria disparar por
    accidente con un simple prefetch del navegador o un crawler.
    """

    def post(self, request, product_id):
        try:
            products_api.delete_product(product_id)
            messages.success(request, 'Producto retirado del catalogo.')
        except APINotFound:
            messages.info(request, 'El producto ya habia sido retirado.')
        except APIUnavailable as error:
            messages.error(request, error.mensaje_usuario)
        return redirect('catalog:manage_product_list')
