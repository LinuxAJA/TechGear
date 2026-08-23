"""Constantes del catalogo.

Las categorias reflejan la enumeracion Category de la API. Se replican aqui
solo para construir el desplegable del filtro; la validacion real la hace la
API, que rechaza cualquier valor que no conozca.
"""

CATEGORIES = [
    ('cpu', 'Procesadores'),
    ('gpu', 'Tarjetas graficas'),
    ('ram', 'Memorias RAM'),
    ('storage', 'Almacenamiento'),
    ('peripheral', 'Perifericos'),
    ('accessory', 'Accesorios'),
]
