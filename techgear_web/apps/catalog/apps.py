from django.apps import AppConfig

class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # Debe coincidir con la ruta de importacion real del paquete. Django genera
    # 'catalog' al usar startapp, pero la app vive dentro del paquete apps/.
    name = 'apps.catalog'
    verbose_name = 'Catalogo de Productos'