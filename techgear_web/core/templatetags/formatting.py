"""Filtros de plantilla para presentar datos que llegan de la API.

Para que Django descubra este modulo, `core` debe estar en INSTALLED_APPS y el
paquete debe tener __init__.py: las etiquetas personalizadas solo se buscan
dentro de aplicaciones instaladas.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def cop(value: object) -> str:
    """Formatea un precio en pesos colombianos.

    La API envia los precios como cadena ("3299900.00") en lugar de numero,
    porque Decimal serializado a texto conserva los centavos exactos. Aqui se
    convierte a Decimal y se presenta con separador de miles: $ 3.299.900

    Se omiten los centavos cuando son cero, que es lo habitual en pesos.
    """
    try:
        cantidad = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return str(value)

    entero, centavos = divmod(cantidad, 1)
    # El formato de Python usa la coma como separador de miles; en Colombia se
    # usa el punto, asi que se intercambian.
    miles = f'{int(entero):,}'.replace(',', '.')

    if centavos:
        return f'$ {miles},{int(centavos * 100):02d}'
    return f'$ {miles}'


@register.filter
def categoria(value: object) -> str:
    """Traduce el valor de categoria de la API a una etiqueta legible."""
    etiquetas = {
        'cpu': 'Procesadores',
        'gpu': 'Tarjetas graficas',
        'ram': 'Memorias RAM',
        'storage': 'Almacenamiento',
        'peripheral': 'Perifericos',
        'accessory': 'Accesorios',
    }
    return etiquetas.get(str(value), str(value).capitalize())


@register.filter
def iso_datetime(value: object) -> str:
    """Formatea una fecha ISO 8601 (como la devuelve la API) de forma legible.

    La API serializa las fechas como texto ISO 8601 en UTC. Al llegar como
    JSON, Django no las reconoce como objetos de fecha automaticamente (son
    texto plano), asi que el filtro |date de Django no funciona sobre ellas:
    hay que parsearlas primero. De paso se convierten a la zona horaria del
    proyecto (America/Bogota) en vez de mostrar la hora UTC cruda.
    """
    if not value:
        return ''
    try:
        fecha = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return str(value)

    if timezone.is_aware(fecha):
        fecha = timezone.localtime(fecha)
    return fecha.strftime('%d/%m/%Y %H:%M')
