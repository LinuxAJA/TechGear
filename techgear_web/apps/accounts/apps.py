from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # Debe coincidir con la ruta de importacion real del paquete (apps.accounts),
    # no con 'accounts' que es lo que generaria un startapp sin mover la carpeta.
    name = 'apps.accounts'
    verbose_name = 'Cuentas de usuario'
