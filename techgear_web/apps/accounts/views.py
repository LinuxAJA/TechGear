"""Vistas de cuentas de usuario.

El login y el logout usan las vistas INTEGRADAS de Django
(django.contrib.auth.views), configuradas directamente en las URLs: escribir
esa logica a mano es el error clasico de reinventar el manejo de sesiones y
contraseñas. Aqui solo se define el registro, que Django no trae de fabrica.
"""

from django.contrib import messages
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.views.generic import CreateView

from apps.accounts.forms import RegisterForm


class RegisterView(CreateView):
    """Alta de un nuevo usuario del portal."""

    form_class = RegisterForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('catalog:product_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Inicia sesion automaticamente: pedirle al usuario que se registre y
        # luego vuelva a escribir sus credenciales en el login es friccion
        # innecesaria.
        login(self.request, self.object)
        messages.success(self.request, f'¡Bienvenido, {self.object.username}! Tu cuenta fue creada correctamente.')
        return response
