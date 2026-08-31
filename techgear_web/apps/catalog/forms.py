"""Formularios de gestion de productos (seccion staff del portal).

Reflejan ProductCreate / ProductUpdate de techgear_api/app/schemas/product.py.
Son forms.Form, no ModelForm: no hay un modelo local de Producto. La
autoridad final sigue siendo la API; el error 409 por SKU duplicado se
inyecta sobre el campo `sku` desde la vista, no se valida aqui contra nada
propio (el portal no tiene forma de saber que SKUs existen sin preguntarle a
la API).
"""

import re
from decimal import Decimal

from django import forms

from apps.catalog.constants import CATEGORIES

SKU_PATTERN = re.compile(r'^[A-Z0-9\-]{4,20}$')


class ProductCreateForm(forms.Form):
    """Cuerpo del formulario de alta. Corresponde a ProductCreate."""

    sku = forms.CharField(
        label='SKU',
        max_length=20,
        help_text='4 a 20 caracteres: mayusculas, numeros y guiones. No se puede cambiar despues.',
        widget=forms.TextInput(attrs={'placeholder': 'GPU-RTX4070-01'}),
    )
    name = forms.CharField(label='Nombre', min_length=3, max_length=120)
    description = forms.CharField(
        label='Descripcion', max_length=1000, required=False, widget=forms.Textarea(attrs={'rows': 4})
    )
    category = forms.ChoiceField(label='Categoria', choices=CATEGORIES)
    price = forms.DecimalField(label='Precio', min_value=Decimal('0.01'), max_digits=12, decimal_places=2)
    stock = forms.IntegerField(label='Stock inicial', min_value=0)
    image_url = forms.URLField(label='URL de la imagen', required=False)

    def clean_sku(self) -> str:
        sku = self.cleaned_data['sku'].strip().upper()
        if not SKU_PATTERN.match(sku):
            raise forms.ValidationError('El SKU debe tener entre 4 y 20 caracteres: mayusculas, numeros y guiones.')
        return sku


class ProductUpdateForm(forms.Form):
    """Cuerpo del formulario de edicion. Corresponde a ProductUpdate.

    No incluye `sku`: la API no lo acepta en la actualizacion porque es la
    clave de negocio del producto y no deberia cambiar tras crearlo.
    """

    name = forms.CharField(label='Nombre', min_length=3, max_length=120)
    description = forms.CharField(
        label='Descripcion', max_length=1000, required=False, widget=forms.Textarea(attrs={'rows': 4})
    )
    category = forms.ChoiceField(label='Categoria', choices=CATEGORIES)
    price = forms.DecimalField(label='Precio', min_value=Decimal('0.01'), max_digits=12, decimal_places=2)
    stock = forms.IntegerField(label='Stock', min_value=0)
    image_url = forms.URLField(label='URL de la imagen', required=False)
    is_active = forms.BooleanField(label='Visible en el catalogo', required=False)
