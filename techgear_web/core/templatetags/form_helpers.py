"""Filtros para renderizar formularios con las clases de Tailwind del proyecto.

Sin una libreria como django-widget-tweaks, Django renderiza cada campo con su
widget por defecto, sin las clases del tema. `add_class` reconstruye el widget
con los atributos que le pasemos, lo que evita esa dependencia extra para un
solo filtro.
"""

from django import template

register = template.Library()


@register.filter(name='add_class')
def add_class(field, css_classes: str):
    """Renderiza un campo de formulario con clases CSS adicionales.

    Uso: {{ form.username|add_class:"w-full rounded-lg border ..." }}
    """
    return field.as_widget(attrs={**field.field.widget.attrs, 'class': css_classes})
