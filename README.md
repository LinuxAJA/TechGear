# TechGear — Sistema Híbrido de Catálogo y Pedidos

Sistema web híbrido para una tienda de hardware y accesorios tecnológicos.

- **`techgear_api/`** — microservicio REST construido con **FastAPI**, que administra el
  inventario y los pedidos sobre **MongoDB Atlas** y documenta su contrato con **Swagger UI**.
- **`techgear_web/`** — portal web construido con **Django** (patrón MVT), que consume esa API
  por HTTP para mostrar el catálogo y permitir la creación de pedidos.

---

## Enlaces de los servicios desplegados

| Servicio | Entorno | Enlace |
|---|---|---|
| API — Documentación interactiva (Swagger UI) | Render | _pendiente de desplegar_ |
| API — Estado del servicio | Render | _pendiente de desplegar_ |
| API — URL base | Render | _pendiente de desplegar_ |
| Portal web (Django) | — | _pendiente de desplegar_ |
| Repositorio | GitHub | https://github.com/LinuxAJA/TechGear |

> **El primer acceso puede tardar.** La API se despliega en el plan gratuito de Render, que
> duerme el servicio tras 15 minutos sin tráfico y tarda cerca de un minuto en volver a
> levantarlo. Si Swagger no carga de inmediato, abre primero `/health`, espera a que responda y
> vuelve a intentarlo: a partir de ahí el servicio responde con normalidad.

---

## Arquitectura

```
Navegador ──HTML──> Django (MVT, :8000) ──HTTP/JSON──> FastAPI (:8001) ──> MongoDB Atlas
                         │
                         └── SQLite (solo autenticación: usuarios y sesiones)
```

**Regla de oro:** Django nunca habla con MongoDB y FastAPI nunca renderiza HTML. El único
contrato entre ambos servicios es JSON sobre `/api/v1`.

### Capas de la API

```
endpoints  →  services  →  repositories  →  MongoDB
   HTTP        negocio        datos
```

Las dependencias van en una sola dirección. Un endpoint no arma consultas de MongoDB y un
repositorio no lanza errores HTTP. Esto permite probar las reglas de negocio con un repositorio
falso en memoria, sin conexión a Atlas.

> **Nota sobre el driver:** se usa **Motor** por fidelidad con el ejemplo visto en clase. Motor
> quedó deprecado en 2025 en favor del soporte asíncrono nativo de PyMongo (`AsyncMongoClient`).
> Todo su uso está confinado a `app/db/mongodb.py` y `app/repositories/`, de modo que migrar en
> el futuro es un cambio localizado.

---

## Estructura del proyecto

```
techGear/
├── techgear_api/                  # ── FastAPI ──
│   ├── app/
│   │   ├── main.py                # composición: app, lifespan y routers
│   │   ├── core/
│   │   │   ├── config.py          # Settings validadas con pydantic-settings
│   │   │   ├── exceptions.py      # excepciones de dominio (sin HTTP)
│   │   │   └── handlers.py        # traduce esas excepciones a códigos HTTP
│   │   ├── db/
│   │   │   ├── mongodb.py         # cliente Motor: conectar, cerrar, obtener base
│   │   │   └── indexes.py         # índices creados al arrancar (idempotentes)
│   │   ├── schemas/               # DTOs de entrada y salida (Pydantic)
│   │   ├── repositories/          # capa de datos (único lugar que conoce BSON)
│   │   ├── services/              # capa de negocio (stock, totales, estados)
│   │   └── api/
│   │       ├── deps.py            # inyección de dependencias
│   │       └── v1/                # routers y endpoints versionados
│   ├── tests/                     # pruebas con repositorio falso en memoria
│   ├── pytest.ini
│   ├── .python-version            # versión de Python fijada para el despliegue
│   ├── .env.example
│   ├── requirements.txt           # solo producción
│   └── requirements-dev.txt       # producción + dependencias de prueba
│
└── techgear_web/                  # ── Django (patrón MVT) ──
    ├── manage.py
    ├── config/                    # proyecto: settings por entorno, urls, wsgi
    ├── core/                      # app de utilidades transversales
    │   ├── api/
    │   │   ├── client.py          # ÚNICO módulo que usa requests (Gateway)
    │   │   ├── exceptions.py      # APINotFound, APIValidationError, APIUnavailable
    │   │   ├── products.py        # operaciones del catálogo
    │   │   └── orders.py          # pedidos (pendiente)
    │   └── templatetags/
    │       ├── formatting.py      # filtros |cop y |categoria
    │       └── catalog_tags.py    # inclusion_tag, simple_tag y filtros de stock
    ├── apps/
    │   ├── catalog/               # listado y detalle de productos
    │   └── orders/                # carrito y pedidos (pendiente)
    ├── templates/                 # base.html, includes/, catalog/, errors/
    ├── static/
    │   ├── src/input.css          # fuente de Tailwind (se edita)
    │   └── css/tailwind.css       # generado por la CLI (se versiona)
    ├── package.json               # toolchain de Tailwind
    ├── .env.example
    └── requirements.txt
```

En la raíz del repositorio, `render.yaml` describe el despliegue del backend.

---

## Requisitos previos

- **Python 3.11** o superior
- Una cuenta de **MongoDB Atlas** con un clúster creado
- **Node.js 22** — solo si se van a modificar los estilos (Tailwind CSS)

---

## Puesta en marcha

### 1. Obtener la cadena de conexión de MongoDB Atlas

En Atlas: **Database → Connect → Drivers**. Se recomienda crear un usuario dedicado con rol
`readWrite` únicamente sobre la base `techgear_db` (principio de mínimo privilegio) y restringir
el acceso de red a la IP propia en **Network Access**.

### 2. Levantar la API (terminal 1)

```bash
cd techgear_api

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / macOS

# requirements.txt trae solo lo de produccion; para desarrollar y correr las
# pruebas se instala requirements-dev.txt, que incluye al primero.
pip install -r requirements-dev.txt

copy .env.example .env         # Windows  (cp en Linux/macOS)
# Editar .env y completar MONGODB_URL

uvicorn app.main:app --reload --port 8001
```

Al arrancar debe verse en la consola `Conexion a MongoDB Atlas exitosa`.

| Recurso | URL |
|---|---|
| Documentación interactiva (Swagger UI) | http://localhost:8001/docs |
| Documentación alternativa (ReDoc) | http://localhost:8001/redoc |
| Estado del servicio | http://localhost:8001/health |

### 3. Levantar el portal Django (terminal 2)

La API debe estar corriendo primero: el portal no tiene datos propios, los pide por HTTP.

```bash
cd techgear_web

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / macOS

pip install -r requirements.txt

copy .env.example .env         # Windows  (cp en Linux/macOS)
# Generar una SECRET_KEY con:
# python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"

python manage.py migrate       # crea SQLite: solo usuarios y sesiones
python manage.py runserver 8000
```

El portal queda en http://localhost:8000

### 4. Recompilar los estilos (solo si se tocan plantillas o `input.css`)

Tailwind está instalado como dependencia del proyecto, **no se usa el CDN**. El archivo generado
`static/css/tailwind.css` se versiona a propósito, para que el proyecto se pueda clonar y ejecutar
sin instalar Node.

```bash
cd techgear_web
npm install
npm run dev:css        # modo watch durante el desarrollo
npm run build:css      # compilado minificado para la entrega
```

---

## Rutas del portal

| Ruta | Vista | Descripción |
|---|---|---|
| `/` | `ProductListView` | Catálogo: listado con búsqueda (`?q=`), filtro (`?category=`) y paginación (`?page=`) |
| `/producto/<id>/` | `ProductDetailView` | Ficha del producto. Un identificador inexistente devuelve `404` |
| `/admin/` | Django admin | Administración de usuarios y sesiones |

## Template tags propios

El catálogo se renderiza con etiquetas de plantilla escritas para el proyecto, en
[`techgear_web/core/templatetags/`](techgear_web/core/templatetags/). Django ofrece tres formas
de extender el lenguaje de plantillas y aquí se usa una de cada tipo, porque cada una resuelve un
problema distinto:

| Tag | Tipo | Uso | Qué resuelve |
|---|---|---|---|
| `{% product_card producto %}` | `inclusion_tag` | Tarjeta de producto | Recibe el producto como argumento explícito. Con `{% include %}` la tarjeta dependía de forma invisible de que existiera una variable llamada `product` en el contexto exterior |
| `{% query_string page=2 %}` | `simple_tag` (`takes_context`) | Enlaces que conservan filtros | Parte de los parámetros reales de la petición. Antes cada enlace concatenaba cadenas con un `{% if %}` por filtro, y bastaba olvidar uno para perder la búsqueda al cambiar de página |
| `\|cop`, `\|categoria` | `filter` | Precio y categoría legibles | La API envía el precio como cadena (`"3299900.00"`) para no perder centavos; el filtro lo presenta como `$ 3.299.900` |
| `\|stock_label`, `\|stock_classes` | `filter` | Estado del inventario | Texto y color del distintivo se deciden juntos, en un solo sitio, para que no se desincronicen |

> **Detalle de sintaxis que conviene recordar:** `{# ... #}` es un comentario de **una sola
> línea**. Si se parte en dos, Django deja de reconocerlo como comentario, vuelca el texto al HTML
> y **ejecuta las etiquetas que haya dentro**. Para varias líneas hay que usar
> `{% comment %} ... {% endcomment %}`.

## Integración HTTP con la API

El consumo de la API con la librería **`requests`** vive en un único módulo:
**[`techgear_web/core/api/client.py`](techgear_web/core/api/client.py)**.

Está centralizado ahí, y no repetido en cada vista, por cuatro razones concretas:

1. Una sola `requests.Session` reutiliza la conexión TCP/TLS entre peticiones.
2. El **timeout siempre se aplica**. Una petición sin timeout puede dejar colgada la vista de
   Django indefinidamente si la API no responde.
3. Los reintentos ante fallos transitorios (502/503/504) se configuran una vez, y solo para
   métodos idempotentes: repetir un `POST` podría crear dos pedidos.
4. Los códigos HTTP se traducen a excepciones tipadas (`APINotFound`, `APIValidationError`,
   `APIUnavailable`) en un solo lugar, de modo que las vistas manejan errores de negocio y no
   números.

Encima del cliente, `core/api/products.py` expone las operaciones del catálogo. Ninguna vista
importa `requests` directamente: es el patrón **Gateway** o capa anticorrupción.

Si la API está caída, el portal responde **503** con la página `errors/api_unavailable.html` en
lugar de una traza de error.

## ¿Por qué `models.py` está vacío?

No es un descuido. En esta arquitectura híbrida **el modelo de dominio es remoto**: los productos
y los pedidos viven en MongoDB Atlas y se consultan a través de la API. El portal no los replica
en un ORM porque tener dos fuentes de verdad para el mismo dato es exactamente lo que se quiere
evitar. La "M" del patrón MVT la aporta la API; Django pone la Vista y la Plantilla.

La base SQLite del portal existe únicamente para `django.contrib.auth`: usuarios y sesiones, que
sí son responsabilidad del frontend.

---

## Variables de entorno

Ningún archivo `.env` se versiona. Cada servicio incluye su `.env.example` con la lista completa
de variables y valores de ejemplo.

### `techgear_api/.env`

| Variable | Descripción | Ejemplo |
|---|---|---|
| `MONGODB_URL` | Cadena de conexión de Atlas | `mongodb+srv://<usuario>:<password>@<cluster>.mongodb.net/` |
| `MONGODB_DB` | Base de datos de la aplicación | `techgear_db` |
| `MONGODB_TEST_DB` | Base de datos usada por las pruebas | `techgear_test` |
| `API_V1_PREFIX` | Prefijo de la versión de la API | `/api/v1` |
| `CORS_ORIGINS` | Orígenes permitidos, separados por coma | `http://localhost:8000` |
| `DEBUG` | Modo depuración | `True` |

### `techgear_web/.env`

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DJANGO_SECRET_KEY` | Clave criptográfica de Django | `clave-solo-para-desarrollo` |
| `DJANGO_DEBUG` | Modo depuración | `True` |
| `DJANGO_ALLOWED_HOSTS` | Hosts autorizados | `localhost,127.0.0.1` |
| `TECHGEAR_API_BASE_URL` | URL base de la API | `http://localhost:8001/api/v1` |
| `TECHGEAR_API_TIMEOUT` | Segundos de espera por petición | `10` (local) / `30` (Render) |
| `TECHGEAR_API_RETRIES` | Reintentos ante 502/503/504 | `3` (local) / `5` (Render) |
| `TECHGEAR_API_BACKOFF` | Factor de espera exponencial entre reintentos | `0.3` (local) / `2` (Render) |

---

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/health` | Estado del servicio y de la conexión a MongoDB |
| `GET` | `/api/v1/products` | Listado paginado con búsqueda (`q`), filtro por categoría y por estado |
| `POST` | `/api/v1/products` | Crear producto. Devuelve `409` si el SKU ya existe |
| `GET` | `/api/v1/products/{id}` | Consultar producto por identificador |
| `PATCH` | `/api/v1/products/{id}` | Actualización parcial: solo cambian los campos enviados |
| `DELETE` | `/api/v1/products/{id}` | Borrado lógico (`is_active = false`). Devuelve `204` |
| `POST` | `/api/v1/orders` | Registrar pedido. Calcula el total y descuenta inventario |
| `GET` | `/api/v1/orders` | Listado paginado, filtrable por `customer` y `status` |
| `GET` | `/api/v1/orders/{id}` | Consultar pedido por identificador |
| `PATCH` | `/api/v1/orders/{id}/status` | Cambiar estado validando la transición |

### Estados de un pedido

```
pending ──> paid ──> shipped ──> delivered
   │         │
   └─────────┴──> cancelled   (devuelve las unidades al inventario)
```

`delivered` y `cancelled` son estados finales. Cualquier otra transición responde `409`.

### Códigos de error

Todos los errores comparten la misma forma, para que el portal Django los interprete con un
solo bloque de código:

```json
{ "detail": "Stock insuficiente para 'RTX 4070': se solicitaron 99 unidades y solo hay 8 disponibles.", "code": "insufficient_stock" }
```

| Código HTTP | Cuándo ocurre |
|---|---|
| `404` | `product_not_found`, `order_not_found` |
| `409` | `duplicate_sku`, `insufficient_stock`, `inactive_product`, `invalid_status_transition` |
| `422` | Validación de Pydantic: identificador mal formado, campos inválidos o faltantes |

---

## Decisiones de diseño

- **Un esquema Pydantic por dirección del dato** (`Create`, `Update`, `Public`). El cliente no
  puede enviar campos que controla el servidor, y la respuesta expone solo lo previsto.
- **`Decimal` y no `float` para los precios.** Los flotantes binarios no representan dinero de
  forma exacta y el error se acumula al sumar los totales de un pedido.
- **El precio de un pedido siempre se lee de la base de datos.** El cliente envía únicamente el
  identificador del producto y la cantidad.
- **Cada línea de pedido guarda un *snapshot*** del SKU, el nombre y el precio del momento de la
  compra: un cambio de precio futuro no altera el total de un pedido pasado.
- **Borrado lógico de productos** (`is_active = false`). Los pedidos históricos referencian
  productos; borrarlos físicamente los dejaría huérfanos.

---

## Pruebas

```bash
cd techgear_api
venv\Scripts\activate
pip install -r requirements-dev.txt   # si aun no estan instaladas
pytest
```

Las pruebas de servicio usan un **repositorio falso en memoria** que implementa la misma
interfaz que el repositorio real. Por eso corren en menos de un segundo, no necesitan conexión
a MongoDB Atlas y no dejan datos de prueba en la base. Cubren el cálculo de totales, el
*snapshot* de precios, el descuento de inventario, la reposición ante un fallo parcial, las
transiciones de estado y el borrado lógico.

---

## Despliegue

El backend se despliega en **Render** a partir de [`render.yaml`](render.yaml), que deja la
configuracion versionada junto al codigo en lugar de repartida por un panel.

| Ajuste | Valor | Por que |
|---|---|---|
| `rootDir` | `techgear_api` | El repositorio es un monorepo: Render construye solo el backend |
| `buildCommand` | `pip install -r requirements.txt` | Solo dependencias de produccion |
| `startCommand` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` | `--host 0.0.0.0` es obligatorio: por defecto uvicorn escucha en `127.0.0.1` y Render no podria enrutar el trafico. `$PORT` lo asigna la plataforma |
| `healthCheckPath` | `/health` | Ya existia y comprueba tambien la conexion con Atlas |
| `.python-version` | `3.11.9` | Sin fijarla, Render compila con su version por defecto (hoy 3.14.3), distinta a la de desarrollo |

`MONGODB_URL` se declara con `sync: false`: Render la pide al crear el servicio y la guarda
cifrada. **Nunca se escribe en el repositorio.**

### Acceso desde Atlas

El plan gratuito de Render no ofrece IP de salida fija, asi que **Network Access** debe permitir
`0.0.0.0/0`. Es una concesion obligada del plan, no un descuido: lo que sigue protegiendo la base
es la autenticacion, con un usuario que tiene `readWrite` unicamente sobre `techgear_db` y
`techgear_test`, no sobre el cluster. Al pasar a un plan de pago, el camino correcto es volver a
restringir por las IP estaticas de Render.

### Apuntar el portal a la API desplegada

En `techgear_web/.env`, cambiar la URL base y ampliar los margenes de espera, porque el servicio
gratuito se duerme tras 15 minutos sin trafico:

```
TECHGEAR_API_BASE_URL=https://<tu-servicio>.onrender.com/api/v1
TECHGEAR_API_TIMEOUT=30
TECHGEAR_API_RETRIES=5
TECHGEAR_API_BACKOFF=2
```

Con `backoff=2` y 5 intentos se esperan 0, 2, 4, 8 y 16 segundos: 30 segundos acumulados,
suficientes para cubrir el arranque en frio. Con los valores de desarrollo (10 s de espera y
reintentos de menos de un segundo) la primera visita al portal tras un rato de inactividad
mostraria la pagina de servicio no disponible aunque el backend estuviera sano.

---

## Autor

Lino Andrés Aguirre — Taller 2, FastAPI + Django.
