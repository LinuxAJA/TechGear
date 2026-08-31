"""Formularios de la app de cuentas.

No se escribe manejo de contraseñas a mano: se hereda de UserCreationForm, que
ya aplica los validadores de AUTH_PASSWORD_VALIDATORS y guarda el hash con el
algoritmo configurado en Django. Solo se añade el campo de correo, que
UserCreationForm no incluye por defecto.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegisterForm(UserCreationForm):
    """Registro de un nuevo usuario del portal."""

    email = forms.EmailField(
        required=True,
        label='Correo electronico',
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
