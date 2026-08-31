"""Vistas de carrito, checkout e historial de pedidos."""

import logging
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import FormView, TemplateView

from apps.orders.cart import Cart, resolve_cart_lines
from apps.orders.forms import CheckoutForm
from core.api import orders as orders_api
from core.api.exceptions import APINotFound, APIUnavailable, APIValidationError
from core.mixins import APIErrorHandlingMixin

logger = logging.getLogger(__name__)


def _safe_redirect_target(request, fallback: str) -> str:
    """Valida `next` antes de redirigir, para evitar un open redirect.

    El formulario "Agregar al carrito" viaja con un campo oculto `next` para
    devolver al usuario a donde estaba (catalogo o detalle). Sin esta
    validacion, alguien podria construir un enlace que redirija a un sitio
    externo despues de la peticion.
    """
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return fallback


class CartView(APIErrorHandlingMixin, TemplateView):
    """Muestra el carrito y permite actualizar cantidades en bloque."""

    template_name = 'orders/cart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = Cart(self.request)
        lineas, retirados = resolve_cart_lines(cart)

        if retirados:
            messages.warning(
                self.request,
                f'Se quitaron {len(retirados)} producto(s) del carrito: ya no estan disponibles.',
            )

        context['lines'] = lineas
        context['total'] = sum((linea.subtotal for linea in lineas), Decimal('0'))
        return context

    def post(self, request, *args, **kwargs):
        """Actualiza las cantidades enviadas desde la propia pagina del carrito."""
        cart = Cart(request)
        for key, value in request.POST.items():
            if not key.startswith('quantity_'):
                continue
            product_id = key.removeprefix('quantity_')
            try:
                cantidad = int(value)
            except (TypeError, ValueError):
                continue
            cart.set_quantity(product_id, cantidad)

        messages.success(request, 'Carrito actualizado.')
        return redirect('orders:cart')


class CartAddView(View):
    """Agrega un producto al carrito. No consulta la API: eso lo hace CartView
    al mostrar el carrito. Aqui solo se escribe en la sesion."""

    def post(self, request, product_id):
        try:
            cantidad = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            cantidad = 1

        Cart(request).add(product_id, max(cantidad, 1))
        messages.success(request, 'Producto agregado al carrito.')
        return redirect(_safe_redirect_target(request, reverse('orders:cart')))


class CartRemoveView(View):
    """Quita un producto del carrito."""

    def post(self, request, product_id):
        Cart(request).remove(product_id)
        messages.info(request, 'Producto eliminado del carrito.')
        return redirect('orders:cart')


class CheckoutView(LoginRequiredMixin, APIErrorHandlingMixin, FormView):
    """Captura los datos del comprador y registra el pedido en la API.

    Es la vista central de la Clase 5: un formulario HTML en el template que,
    al enviarse, hace un POST hacia el endpoint de FastAPI. El precio nunca
    sale de aqui: solo product_id y quantity, tal como exige OrderCreate.
    """

    form_class = CheckoutForm
    template_name = 'orders/checkout.html'

    def dispatch(self, request, *args, **kwargs):
        # El chequeo de carrito vacio solo aplica a quien ya paso el control
        # de LoginRequiredMixin: si se evaluara antes, un usuario anonimo con
        # el carrito vacio veria "tu carrito esta vacio" en vez de que se le
        # pida iniciar sesion, que es el mensaje correcto en ese caso.
        if request.user.is_authenticated and Cart(request).is_empty:
            messages.info(request, 'Tu carrito esta vacio.')
            return redirect('catalog:product_list')
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        user = self.request.user
        return {
            'full_name': user.get_full_name() or user.username,
            'email': user.email,
        }

    def get_context_data(self, **kwargs):
        """Arma el contexto reutilizando `self._cart_lines` si ya se calculo.

        form_invalid() vuelve a llamar a get_context_data() para re-renderizar
        el formulario con errores, y eso volveria a golpear la API una
        segunda vez en el mismo request. Si form_valid() ya resolvio (o
        intento resolver) el carrito, ese resultado se reutiliza aqui en vez
        de repetir la llamada, que es justo el escenario donde repetirla
        volveria a fallar con la API caida.
        """
        context = super().get_context_data(**kwargs)

        if not hasattr(self, '_cart_lines'):
            # Primera vez en este request (GET normal): si la API esta caida,
            # la excepcion se deja propagar para que APIErrorHandlingMixin.get()
            # la convierta en la pagina de servicio no disponible.
            self._cart_lines, retirados = resolve_cart_lines(Cart(self.request))
            if retirados:
                messages.warning(
                    self.request,
                    f'Se quitaron {len(retirados)} producto(s) del carrito: ya no estan disponibles.',
                )

        context['lines'] = self._cart_lines
        context['total'] = sum((linea.subtotal for linea in self._cart_lines), Decimal('0'))
        return context

    def form_valid(self, form):
        cart = Cart(self.request)
        # Se revalida justo antes de enviar: el stock pudo cambiar entre que
        # se cargo el formulario y que el usuario le dio a "Confirmar". Esta
        # llamada ocurre dentro de post(), fuera del alcance de
        # APIErrorHandlingMixin (que solo envuelve get()), asi que el fallo de
        # infraestructura se maneja aqui explicitamente: el carrito NO se
        # toca, para que el usuario pueda reintentar cuando la API vuelva.
        try:
            self._cart_lines, retirados = resolve_cart_lines(cart)
        except APIUnavailable as error:
            logger.error('API no disponible al revalidar el carrito en checkout: %s', error.detail)
            messages.error(self.request, error.mensaje_usuario)
            # Se cachea una lista vacia: si no, form_invalid() dispararia
            # get_context_data(), que volveria a llamar a resolve_cart_lines()
            # y crashearia por segunda vez contra una API que ya sabemos caida.
            self._cart_lines = []
            return self.form_invalid(form)

        lineas = self._cart_lines
        if not lineas:
            messages.error(self.request, 'Tu carrito quedo vacio: los productos ya no estan disponibles.')
            return redirect('catalog:product_list')

        if retirados:
            messages.warning(
                self.request,
                f'Se quitaron {len(retirados)} producto(s) del carrito antes de confirmar el pedido.',
            )

        customer = {
            'username': self.request.user.username,
            'full_name': form.cleaned_data['full_name'],
            'email': form.cleaned_data['email'],
            'phone': form.cleaned_data['phone'],
            'address': form.cleaned_data['address'],
            'city': form.cleaned_data['city'],
        }
        items = [{'product_id': linea.product['id'], 'quantity': linea.quantity} for linea in lineas]

        try:
            order = orders_api.create_order(customer=customer, items=items, notes=form.cleaned_data['notes'])
        except (APINotFound, APIValidationError) as error:
            # 404: algun producto desaparecio en el instante final.
            # 409/422: stock insuficiente, producto retirado o datos invalidos.
            # Cualquiera de los dos es algo que el usuario puede corregir
            # ajustando el carrito, asi que se muestra sobre el formulario.
            form.add_error(None, error.detail)
            return self.form_invalid(form)
        except APIUnavailable as error:
            # Un POST no es idempotente: NO se reintenta solo. Se conserva el
            # carrito intacto para que el usuario pueda reintentar el envio.
            logger.error('API no disponible al registrar un pedido: %s', error.detail)
            messages.error(self.request, error.mensaje_usuario)
            return self.form_invalid(form)

        cart.clear()
        messages.success(self.request, f'¡Pedido {order["order_number"]} registrado con exito!')
        return redirect('orders:order_detail', order_id=order['id'])


class OrderListView(LoginRequiredMixin, APIErrorHandlingMixin, TemplateView):
    """Historial de pedidos del usuario autenticado."""

    template_name = 'orders/order_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pagina = orders_api.list_orders(customer=self.request.user.username, page_size=50)
        context['orders'] = pagina['items']
        return context


class OrderDetailView(LoginRequiredMixin, APIErrorHandlingMixin, TemplateView):
    """Detalle de un pedido propio.

    La API no valida propiedad: GET /orders/{id} devuelve cualquier pedido a
    quien conozca su identificador. La comprobacion de que el pedido
    pertenece al usuario autenticado se hace aqui, y su ausencia se trata
    exactamente igual que un pedido inexistente (404), para no revelar que
    el id pertenece a otra persona.
    """

    template_name = 'orders/order_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            order = orders_api.get_order(kwargs['order_id'])
        except APINotFound as error:
            raise Http404('El pedido solicitado no existe.') from error

        if order['customer']['username'] != self.request.user.username:
            raise Http404('El pedido solicitado no existe.')

        context['order'] = order
        return context


class OrderCancelView(LoginRequiredMixin, View):
    """Cancela un pedido propio. Repone el inventario en la API.

    Es un View simple (no TemplateView), asi que APIErrorHandlingMixin no
    aplica aqui: esta vista nunca renderiza una plantilla propia, siempre
    redirige. Por eso maneja APIUnavailable a mano, con un mensaje y una
    redirigida al detalle (que si mostrara la pagina de servicio no
    disponible si la API sigue caida al recargar).
    """

    def post(self, request, order_id):
        try:
            order = orders_api.get_order(order_id)
        except APINotFound as error:
            raise Http404('El pedido solicitado no existe.') from error
        except APIUnavailable as error:
            messages.error(request, error.mensaje_usuario)
            return redirect('orders:order_list')

        if order['customer']['username'] != request.user.username:
            raise Http404('El pedido solicitado no existe.')

        try:
            orders_api.update_order_status(order_id, 'cancelled')
            messages.success(request, 'Pedido cancelado. Las unidades volvieron al inventario.')
        except APIValidationError as error:
            # Por ejemplo, intentar cancelar un pedido ya entregado.
            messages.error(request, error.detail)
        except APIUnavailable as error:
            messages.error(request, error.mensaje_usuario)

        return redirect('orders:order_detail', order_id=order_id)
