"""Formularios de pedidos.

CheckoutForm es forms.Form y no ModelForm porque no hay un modelo local: los
datos del comprador viajan directo a la API. Sus validaciones REPLICAN las de
CustomerInfo en techgear_api/app/schemas/order.py, pero son solo una capa de
UX: la autoridad final sigue siendo la API, y sus errores 422/409 se inyectan
en este mismo formulario desde CheckoutView (ver apps/orders/views.py).
"""

import re

from django import forms

PHONE_PATTERN = re.compile(r'^[0-9+\s\-]{7,20}$')


class CheckoutForm(forms.Form):
    """Datos de contacto y envio para registrar un pedido."""

    full_name = forms.CharField(
        label='Nombre completo',
        min_length=3,
        max_length=120,
        widget=forms.TextInput(attrs={'autocomplete': 'name', 'placeholder': 'Nombre y apellidos'}),
    )
    email = forms.EmailField(
        label='Correo electronico',
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )
    phone = forms.CharField(
        label='Telefono',
        widget=forms.TextInput(attrs={'autocomplete': 'tel', 'placeholder': '3001234567'}),
    )
    address = forms.CharField(
        label='Direccion de entrega',
        min_length=5,
        max_length=200,
        widget=forms.TextInput(attrs={'autocomplete': 'street-address'}),
    )
    city = forms.CharField(
        label='Ciudad',
        min_length=3,
        max_length=80,
        widget=forms.TextInput(attrs={'autocomplete': 'address-level2'}),
    )
    notes = forms.CharField(
        label='Observaciones para el despacho',
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def clean_phone(self) -> str:
        phone = self.cleaned_data['phone'].strip()
        if not PHONE_PATTERN.match(phone):
            raise forms.ValidationError('Ingresa un telefono valido (solo numeros, espacios, + y -).')
        return phone
