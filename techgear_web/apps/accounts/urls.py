"""Rutas de cuentas de usuario.

login/ y logout/ usan las vistas integradas de Django
(auth_views.LoginView / LogoutView); solo se les indica la plantilla y, en el
caso del logout, a donde redirigir despues de cerrar sesion.
"""

from django.contrib.auth import views as auth_views
from django.urls import path

from apps.accounts.views import RegisterView

app_name = 'accounts'

urlpatterns = [
    path('registro/', RegisterView.as_view(), name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
