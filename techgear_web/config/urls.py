"""Rutas raiz del portal TechGear.

Cada aplicacion declara sus propias rutas y aqui solo se incluyen. El catalogo
se monta en la raiz porque es la vista principal del portal.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.catalog.urls')),
]
