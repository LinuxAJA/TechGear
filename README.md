# TechGear — Sistema Híbrido de Catálogo y Pedidos

Sistema web híbrido para una tienda de hardware y accesorios tecnológicos.

- **`techgear_api/`** — microservicio REST construido con **FastAPI**, que administra el
  inventario y los pedidos sobre **MongoDB Atlas** y documenta su contrato con **Swagger UI**.
- **`techgear_web/`** — portal web construido con **Django** (patrón MVT), que consume esa API
  por HTTP para mostrar el catálogo y permitir la creación de pedidos.

---

## Enlaces de los servicios desplegados

| Servicio                                       | Entorno | Enlace                                        |
| ---------------------------------------------- | ------- | --------------------------------------------- |
| API — Documentación interactiva (Swagger UI) | Render  | https://techgear-api-10pc.onrender.com/docs   |
| API — Estado del servicio                     | Render  | https://techgear-api-10pc.onrender.com/health |
| API — URL base                                | Render  | https://techgear-api-10pc.onrender.com/       |
| Portal web (Django)                            | —      | _pendiente de desplegar_                    |
| Repositorio                                    | GitHub  | https://github.com/LinuxAJA/TechGear          |

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
    │   │   ├── products.py        # operaciones del catálogo (CRUD completo)
    │   │   └── orders.py          # operaciones de pedidos (crear, listar, cancelar)
    │   ├── mixins.py               # APIErrorHandlingMixin, StaffRequiredMixin
    │   └── templatetags/
    │       ├── formatting.py      # filtros |cop, |categoria, |iso_datetime
    │       ├── catalog_tags.py    # inclusion_tag, simple_tag y filtros de stock
    │       └── form_helpers.py    # filtro add_class (formularios con Tailwind)
    ├── apps/
    │   ├── catalog/               # catálogo público + gestión de productos (staff)
    │   ├── accounts/              # registro, login, logout
    │   └── orders/                # carrito en sesión, checkout, historial de pedidos
    ├── templates/                 # base.html, includes/, catalog/, accounts/, orders/, errors/
    ├── tests/                     # pytest-django + requests-mock (corre con la API apagada)
    ├── static/
    │   ├── src/input.css          # fuente de Tailwind (se edita)
    │   └── css/tailwind.css       # generado por la CLI (se versiona)
    ├── package.json               # toolchain de Tailwind
    ├── pytest.ini
    ├── vercel.json                # configuración del despliegue del portal
    ├── .python-version
    ├── .env.example
    ├── requirements.txt           # solo producción
    └── requirements-dev.txt       # producción + dependencias de prueba
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

| Recurso                                 | URL                          |
| --------------------------------------- | ---------------------------- |
| Documentación interactiva (Swagger UI) | http://localhost:8001/docs   |
| Documentación alternativa (ReDoc)      | http://localhost:8001/redoc  |
| Estado del servicio                     | http://localhost:8001/health |

### 3. Levantar el portal Django (terminal 2)

La API debe estar corriendo primero: el portal no tiene datos propios, los pide por HTTP.

```bash
cd techgear_web

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / macOS

# requirements.txt trae solo lo de produccion; requirements-dev.txt lo
# incluye y suma pytest-django y requests-mock para correr las pruebas.
pip install -r requirements-dev.txt

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
| `/cuenta/registro/` | `RegisterView` | Alta de usuario (`UserCreationForm` + correo), con inicio de sesión automático |
| `/cuenta/login/`, `/cuenta/logout/` | `LoginView`, `LogoutView` | Vistas **integradas** de Django, sin lógica de contraseñas propia |
| `/carrito/` | `CartView` | Ver y actualizar cantidades del carrito en sesión |
| `/carrito/agregar/<id>/`, `/carrito/eliminar/<id>/` | `CartAddView`, `CartRemoveView` | Agregar o quitar un producto (solo `POST`) |
| `/checkout/` | `CheckoutView` | Formulario de datos del comprador → `POST /orders`. Requiere sesión iniciada |
| `/mis-pedidos/` | `OrderListView` | Historial de pedidos **del usuario autenticado** |
| `/mis-pedidos/<id>/` | `OrderDetailView` | Detalle de un pedido propio. Ver un pedido ajeno devuelve `404`, no los datos |
| `/mis-pedidos/<id>/cancelar/` | `OrderCancelView` | Cancela un pedido propio y repone el inventario |
| `/gestion/productos/` | `ProductManageListView` | CRUD de productos. Requiere `is_staff=True` |
| `/gestion/productos/nuevo/`, `.../editar/`, `.../eliminar/` | `ProductCreateView`, `ProductUpdateView`, `ProductDeleteView` | Alta, edición y retiro (borrado lógico), todo restringido a staff |
| `/admin/` | Django admin | Administración de usuarios y sesiones |

> **Nota sobre `/gestion/`:** restringir el acceso con `is_staff` es una barrera de **interfaz**,
> no de la API: FastAPI no exige autenticación propia, así que cualquiera que conozca la URL de
> la API podría llamar a `POST /products` directamente. Es una limitación conocida, documentada
> en [Evoluciones futuras](#evoluciones-futuras).

## Template tags propios

El catálogo se renderiza con etiquetas de plantilla escritas para el proyecto, en
[`techgear_web/core/templatetags/`](techgear_web/core/templatetags/). Django ofrece tres formas
de extender el lenguaje de plantillas y aquí se usa una de cada tipo, porque cada una resuelve un
problema distinto:

| Tag                                  | Tipo                               | Uso                           | Qué resuelve                                                                                                                                                                              |
| ------------------------------------ | ---------------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `{% product_card producto %}`      | `inclusion_tag`                  | Tarjeta de producto           | Recibe el producto como argumento explícito. Con`{% include %}` la tarjeta dependía de forma invisible de que existiera una variable llamada `product` en el contexto exterior       |
| `{% query_string page=2 %}`        | `simple_tag` (`takes_context`) | Enlaces que conservan filtros | Parte de los parámetros reales de la petición. Antes cada enlace concatenaba cadenas con un`{% if %}` por filtro, y bastaba olvidar uno para perder la búsqueda al cambiar de página |
| `\|cop`, `\|categoria`             | `filter`                         | Precio y categoría legibles  | La API envía el precio como cadena (`"3299900.00"`) para no perder centavos; el filtro lo presenta como `$ 3.299.900`                                                                 |
| `\|stock_label`, `\|stock_classes` | `filter`                         | Estado del inventario         | Texto y color del distintivo se deciden juntos, en un solo sitio, para que no se desincronicen                                                                                             |

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

## Manejo de excepciones

El flujo de compra tiene cuatro puntos donde algo puede salir mal, y cada uno se maneja de forma
distinta a propósito:

| Caso | Dónde se resuelve | Comportamiento |
|---|---|---|
| **Stock insuficiente al confirmar el pedido** | `CheckoutView.form_valid()` | La API responde `409 insufficient_stock` con un mensaje que ya nombra el producto y las unidades disponibles; se muestra tal cual sobre el formulario con `form.add_error(None, ...)` |
| **El stock cambió mientras el producto estaba en el carrito** | `resolve_cart_lines()` en [`apps/orders/cart.py`](techgear_web/apps/orders/cart.py) | Se revalida contra la API cada vez que se pinta el carrito o el checkout; la cantidad se ajusta al máximo disponible y se avisa **antes** de que el usuario intente pagar |
| **Un producto del carrito fue retirado o borrado** | `resolve_cart_lines()` | Se detecta el `404` de la API, se quita la línea del carrito automáticamente y se informa con un mensaje, en vez de fallar al confirmar |
| **La API se cae justo durante el checkout** | `CheckoutView.form_valid()` | Un `POST` no es idempotente, así que **nunca se reintenta solo**: se muestra un error y el carrito queda intacto para que el usuario reintente cuando el servicio vuelva |

Dos detalles de implementación que costó encontrar y vale la pena dejar anotados:

- **`get_context_data()` se reutiliza a propósito.** Cuando `form_valid()` falla y llama a
  `form_invalid()`, Django vuelve a pedir el contexto para re-renderizar la página. Sin cachear el
  resultado de `resolve_cart_lines()` en `self._cart_lines`, esa segunda llamada repetiría la
  petición a la API — y si la API está caída, provocaría un **segundo** fallo sin capturar.
- **`APIErrorHandlingMixin` solo envuelve `get()`**, no `post()`. Las llamadas a la API que ocurren
  dentro de un `post()` (la revalidación del carrito en `form_valid()`, o `OrderCancelView`) se
  protegen con su propio `try/except`, explícitamente.

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

| Variable            | Descripción                             | Ejemplo                                                       |
| ------------------- | ---------------------------------------- | ------------------------------------------------------------- |
| `MONGODB_URL`     | Cadena de conexión de Atlas             | `mongodb+srv://<usuario>:<password>@<cluster>.mongodb.net/` |
| `MONGODB_DB`      | Base de datos de la aplicación          | `techgear_db`                                               |
| `MONGODB_TEST_DB` | Base de datos usada por las pruebas      | `techgear_test`                                             |
| `API_V1_PREFIX`   | Prefijo de la versión de la API         | `/api/v1`                                                   |
| `CORS_ORIGINS`    | Orígenes permitidos, separados por coma | `http://localhost:8000`                                     |
| `DEBUG`           | Modo depuración                         | `True`                                                      |

### `techgear_web/.env`

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DJANGO_SECRET_KEY` | Clave criptográfica de Django | `clave-solo-para-desarrollo` |
| `DJANGO_DEBUG` | Modo depuración | `True` (local) / `False` (Vercel) |
| `DJANGO_ALLOWED_HOSTS` | Hosts autorizados | `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Dominios HTTPS autorizados a enviar `POST` | vacío (local) / `https://tu-proyecto.vercel.app` |
| `DATABASE_URL` | Postgres para usuarios y sesiones | vacío (local, usa SQLite) / la URL que entrega Neon en Vercel |
| `TECHGEAR_API_BASE_URL` | URL base de la API | `http://localhost:8001/api/v1` |
| `TECHGEAR_API_TIMEOUT` | Segundos de espera por petición | `10` (local) / `30` (Render) |
| `TECHGEAR_API_RETRIES` | Reintentos ante 502/503/504 | `3` (local) / `5` (Render) |
| `TECHGEAR_API_BACKOFF` | Factor de espera exponencial entre reintentos | `0.3` (local) / `2` (Render) |

---

## Endpoints

| Método    | Ruta                           | Descripción                                                               |
| ---------- | ------------------------------ | -------------------------------------------------------------------------- |
| `GET`    | `/health`                    | Estado del servicio y de la conexión a MongoDB                            |
| `GET`    | `/api/v1/products`           | Listado paginado con búsqueda (`q`), filtro por categoría y por estado |
| `POST`   | `/api/v1/products`           | Crear producto. Devuelve`409` si el SKU ya existe                        |
| `GET`    | `/api/v1/products/{id}`      | Consultar producto por identificador                                       |
| `PATCH`  | `/api/v1/products/{id}`      | Actualización parcial: solo cambian los campos enviados                   |
| `DELETE` | `/api/v1/products/{id}`      | Borrado lógico (`is_active = false`). Devuelve `204`                  |
| `POST`   | `/api/v1/orders`             | Registrar pedido. Calcula el total y descuenta inventario                  |
| `GET`    | `/api/v1/orders`             | Listado paginado, filtrable por`customer` y `status`                   |
| `GET`    | `/api/v1/orders/{id}`        | Consultar pedido por identificador                                         |
| `PATCH`  | `/api/v1/orders/{id}/status` | Cambiar estado validando la transición                                    |

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

| Código HTTP | Cuándo ocurre                                                                                 |
| ------------ | ---------------------------------------------------------------------------------------------- |
| `404`      | `product_not_found`, `order_not_found`                                                     |
| `409`      | `duplicate_sku`, `insufficient_stock`, `inactive_product`, `invalid_status_transition` |
| `422`      | Validación de Pydantic: identificador mal formado, campos inválidos o faltantes              |

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

Ninguna de las dos suites necesita que el otro servicio esté corriendo: ambas usan un doble de
prueba (repositorio falso / API simulada) en vez de una dependencia real.

### API (`techgear_api`)

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

### Portal (`techgear_web`)

```bash
cd techgear_web
venv\Scripts\activate
pip install -r requirements-dev.txt   # si aun no estan instaladas
pytest
```

Las 27 pruebas corren **con `techgear_api` completamente apagado**: `requests-mock` intercepta
cada llamada de `requests` antes de que salga a la red, con respuestas que reproducen la forma
exacta de `ProductPublic`/`OrderPublic` (ver `tests/conftest.py`). Cubren, entre otros:

- El catálogo renderiza con datos simulados, y muestra la página de servicio no disponible si la
  API "está caída" (`requests_mock` configurado para lanzar `ConnectionError`).
- `LoginRequiredMixin` redirige a un visitante anónimo desde `/checkout/` y `/mis-pedidos/`.
- El checkout con `409 insufficient_stock` muestra el mensaje sobre el formulario **y conserva
  el carrito**; lo mismo con la API caída durante el envío.
- El carrito consolida cantidades del mismo producto y las ajusta al stock disponible.
- Un usuario no puede ver ni cancelar el pedido de otro (ambos casos devuelven `404`).
- La gestión de productos: `403` para un usuario autenticado sin `is_staff`, y el error de SKU
  duplicado queda anclado al campo correcto del formulario.

---

## Despliegue

El backend se despliega en **Render** a partir de [`render.yaml`](render.yaml), que deja la
configuracion versionada junto al codigo en lugar de repartida por un panel.

| Ajuste              | Valor                                                                                                                                                                                                           | Por que                                                                                          |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `rootDir`         | `techgear_api`                                                                                                                                                                                                | El repositorio es un monorepo: Render construye solo el backend                                  |
| `buildCommand`    | `pip install -r requirements.txt`                                                                                                                                                                             | Solo dependencias de produccion                                                                  |
| `startCommand`    | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` | `--host 0.0.0.0` es obligatorio: por defecto uvicorn escucha en `127.0.0.1` y Render no podria enrutar el trafico. `$PORT` lo asigna la plataforma |                                                                                                  |
| `healthCheckPath` | `/health`                                                                                                                                                                                                     | Ya existia y comprueba tambien la conexion con Atlas                                             |
| `.python-version` | `3.11.9`                                                                                                                                                                                                      | Sin fijarla, Render compila con su version por defecto (hoy 3.14.3), distinta a la de desarrollo |

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

### Portal en Vercel

El portal se despliega en **Vercel** a partir de [`vercel.json`](techgear_web/vercel.json).
Vercel detecta el proyecto Django por su `manage.py` y resuelve el punto de entrada desde
`WSGI_APPLICATION` en `config/settings.py`; no hace falta ningún adaptador.

Tres diferencias frente a correr Django en un servidor propio, todas resueltas en el código:

| Problema | Por qué existe | Solución en el código |
|---|---|---|
| El sistema de archivos no persiste entre invocaciones | Cada petición puede atenderla una instancia distinta de la función | `DATABASE_URL` activa Postgres para usuarios y sesiones; sin ella, SQLite (ver `config/settings.py`) |
| `POST` rechazado con `403` en HTTPS | Django exige declarar los orígenes que pueden enviar formularios | `DJANGO_CSRF_TRUSTED_ORIGINS` con el dominio de Vercel |
| Redirecciones HTTPS en bucle | La conexión real proxy→contenedor es HTTP | `SECURE_PROXY_SSL_HEADER` |

> **El error más fácil de cometer aquí:** olvidar `DJANGO_CSRF_TRUSTED_ORIGINS` no rompe el
> catálogo (son peticiones `GET`) ni el login a simple vista — rompe **el checkout**, que es
> exactamente el flujo que entrega la Clase 5, y solo se nota al intentar confirmar un pedido en
> producción.

**Pasos de despliegue** (panel de Vercel):

1. **Add New → Project**, importar el repositorio. **Root Directory: `techgear_web`** — es
   obligatorio en este monorepo, o Vercel busca `manage.py` en la raíz y no lo encuentra.
2. **Storage → Create Database → Postgres** (Neon) y conectarla al proyecto: define
   `DATABASE_URL` automáticamente.
3. **Settings → Environment Variables**, en *Production*:

   | Variable | Valor |
   |---|---|
   | `DJANGO_SECRET_KEY` | una clave nueva, **distinta a la de desarrollo** |
   | `DJANGO_DEBUG` | `False` |
   | `DJANGO_ALLOWED_HOSTS` | `.vercel.app` |
   | `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://<tu-proyecto>.vercel.app` |
   | `TECHGEAR_API_BASE_URL` | `https://techgear-api-10pc.onrender.com/api/v1` |
   | `TECHGEAR_API_TIMEOUT` / `_RETRIES` / `_BACKOFF` | `30` / `5` / `2` |

4. **Deploy.** Vercel corre `collectstatic` automáticamente (por eso `STATIC_ROOT` está
   definido) y sirve `/static/` desde su CDN.
5. **Migrar la base de datos** — no ocurre sola en el despliegue:
   ```bash
   cd techgear_web
   vercel link
   vercel env pull .env.local     # nunca se versiona: ya está en .gitignore
   # cargar esas variables y ejecutar:
   python manage.py migrate
   python manage.py createsuperuser   # usuario is_staff para /gestion/
   ```
6. En **Render → techgear-api → Environment**, ampliar `CORS_ORIGINS` con el dominio de Vercel.

---

## Evoluciones futuras

Limitaciones conocidas y aceptadas para el alcance de este taller, con el camino correcto para
cuando dejen de serlo:

- **La API no tiene autenticación propia.** `is_staff` en Django restringe la *interfaz* de
  gestión, pero cualquiera que conozca la URL de la API podría llamar a `POST /products`
  directamente. La solución correcta es una clave de servicio o JWT validado en `techgear_api`.
- **El descuento de stock es atómico por documento, no transaccional entre colecciones.**
  MongoDB Atlas corre como *replica set*, así que el paso natural es envolver la creación del
  pedido y el descuento de inventario en una transacción multi-documento.
- **La búsqueda del catálogo usa `$regex`, no un índice de texto.** Suficiente a esta escala;
  con un catálogo grande, [Atlas Search](https://www.mongodb.com/docs/atlas/atlas-search/) daría
  resultados más relevantes y más rápido.
- **Sin CI.** Las dos suites de pruebas corren en local; el paso natural es un workflow de
  GitHub Actions que las ejecute en cada Pull Request.

---

## Autor

Lino Andrés Aguirre — Taller 2, FastAPI + Django.
