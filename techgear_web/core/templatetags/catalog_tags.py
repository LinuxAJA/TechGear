"""Template tags propios del catalogo.

Django ofrece tres formas de extender el lenguaje de plantillas, y aqui se usa
una de cada tipo porque cada una resuelve un problema distinto:

- inclusion_tag : renderiza otra plantilla con un contexto propio y explicito.
- simple_tag    : calcula un valor y lo devuelve como texto.
- filter        : transforma un valor que ya se tiene.

Para que Django los descubra, `core` debe estar en INSTALLED_APPS y el paquete
templatetags debe tener __init__.py.
"""

from django import template
from django.utils.http import urlencode

register = template.Library()


@register.inclusion_tag('includes/_product_card.html')
def product_card(product):
    """Renderiza la tarjeta de un producto.

    Sustituye a {% include "includes/_product_card.html" %}. La diferencia no es
    cosmetica: el include hereda TODO el contexto de la plantilla que lo llama y
    la tarjeta depende, de forma invisible, de que exista una variable llamada
    `product`. El inclusion_tag recibe el producto como argumento, asi que la
    dependencia queda escrita en la llamada y la tarjeta se puede reutilizar
    desde cualquier plantilla, con la variable que sea.
    """
    return {'product': product}


@register.simple_tag(takes_context=True)
def query_string(context, **kwargs):
    """Reconstruye la cadena de consulta conservando los filtros activos.

    Sustituye a la concatenacion manual que habia en la paginacion:

        ?page={{ page|add:'1' }}{% if search %}&q={{ search|urlencode }}{% endif %}...

    Esa forma obliga a repetir un {% if %} por cada filtro en cada enlace, y
    basta olvidar uno para que al pasar de pagina se pierda la busqueda. Aqui se
    parte de los parametros reales de la peticion y solo se reemplazan los que
    se indiquen:

        {% query_string page=2 %}          conserva q y category
        {% query_string category='gpu' %}  cambia la categoria y vuelve a la 1

    Un valor None o vacio elimina el parametro.
    """
    request = context['request']
    params = request.GET.copy()

    for clave, valor in kwargs.items():
        if valor in (None, ''):
            params.pop(clave, None)
        else:
            params[clave] = valor

    if not params:
        return ''

    # doseq=True es obligatorio: request.GET es un QueryDict (un MultiValueDict),
    # y urlencode lo recorre con .lists(), de modo que cada valor llega como
    # lista. Sin doseq, esa lista se serializa con str() y la URL saldria como
    # ?q=%5B%27rtx%27%5D, es decir ?q=['rtx'].
    return f'?{urlencode(params, doseq=True)}'


@register.filter
def stock_label(stock: object) -> str:
    """Traduce las unidades disponibles a un estado legible."""
    try:
        unidades = int(stock)
    except (TypeError, ValueError):
        return 'Sin informacion'

    if unidades <= 0:
        return 'Agotado'
    if unidades <= 5:
        return f'Ultimas {unidades} unidades'
    return f'{unidades} disponibles'


@register.filter
def stock_classes(stock: object) -> str:
    """Devuelve las clases de Tailwind que corresponden al estado del stock.

    Mantener la decision de color junto a la del texto evita que ambas se
    desincronicen, que es lo que pasa cuando el color se decide con un
    {% if %} en cada plantilla donde aparece el producto.
    """
    try:
        unidades = int(stock)
    except (TypeError, ValueError):
        return 'bg-slate-100 text-slate-600'

    if unidades <= 0:
        return 'bg-red-50 text-red-700'
    if unidades <= 5:
        return 'bg-amber-50 text-amber-700'
    return 'bg-emerald-50 text-emerald-700'
