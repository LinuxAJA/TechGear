# TechGear — Sistema Híbrido de Catálogo y Pedidos

Sistema web híbrido para una tienda de hardware y accesorios tecnológicos.

- **`techgear_api/`** — microservicio REST construido con **FastAPI**, que administra el
  inventario y los pedidos sobre **MongoDB Atlas** y documenta su contrato con **Swagger UI**.
- **`techgear_web/`** — portal web construido con **Django** (patrón MVT), que consume esa API
  por HTTP para mostrar el catálogo y permitir la creación de pedidos.

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
│   ├── .env.example
│   └── requirements.txt
│
└── techgear_web/                  # ── Django ── (a partir de la Clase 3)
    ├── .env.example
    └── requirements.txt
```

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

pip install -r requirements.txt

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

> Disponible a partir de la Clase 3.

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
| `TECHGEAR_API_TIMEOUT` | Segundos de espera por petición | `10` |

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
pytest
```

Las pruebas de servicio usan un **repositorio falso en memoria** que implementa la misma
interfaz que el repositorio real. Por eso corren en menos de un segundo, no necesitan conexión
a MongoDB Atlas y no dejan datos de prueba en la base. Cubren el cálculo de totales, el
*snapshot* de precios, el descuento de inventario, la reposición ante un fallo parcial, las
transiciones de estado y el borrado lógico.

---

## Autor

Lino Andrés Aguirre — Taller 2, FastAPI + Django.
