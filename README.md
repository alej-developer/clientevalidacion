# ClienteValidacion - API REST Profesional

API REST de gestion de usuarios construida con FastAPI, arquitectura limpia y Domain-Driven Design simplificado.

[![Tests](https://img.shields.io/badge/tests-30%20passed-brightgreen?style=flat-square&logo=pytest)](https://github.com/alej-developer/clientevalidacion)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square&logo=python)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%20async-red?style=flat-square)](https://www.sqlalchemy.org)
[![License](https://img.shields.io/badge/license-MIT-informational?style=flat-square)](LICENSE)

---

## Tabla de Contenidos

- [Caracteristicas](#caracteristicas)
- [Stack Tecnico](#stack-tecnico)
- [Arquitectura](#arquitectura)
- [Instalacion](#instalacion)
- [Variables de Entorno](#variables-de-entorno)
- [Ejecutar el Servidor](#ejecutar-el-servidor)
- [Endpoints de la API](#endpoints-de-la-api)
- [Autenticacion JWT](#autenticacion-jwt)
- [Rate Limiting](#rate-limiting)
- [Ejecutar Tests](#ejecutar-tests)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Contribuir](#contribuir)

---

## Caracteristicas

- **CRUD completo** de usuarios con validaciones estrictas (email, contrasena)
- **Autenticacion JWT** con `python-jose` - endpoints protegidos con token Bearer
- **Soft Delete** - borrado logico con restauracion sin perdida de datos
- **Reutilizacion de email** tras soft delete (restriccion compuesta `email + eliminado_en`)
- **Busqueda avanzada y ordenacion** - busqueda por texto `q`, filtro por estado y orden dinamico
- **Rate Limiting** con `slowapi` para proteccion contra abuso y ataques de fuerza bruta
- **Arquitectura limpia** - Core -> DB -> Repositorios -> Servicios -> API con capas desacopladas
- **Migraciones asincronas con Alembic** versionadas
- **Suite de pruebas de integracion** con base de datos en memoria aislada por test
- **Documentacion interactiva OpenAPI / Swagger UI** enriquecida con metadatos
- **Logging estructurado** configurable por nivel
- **CORS** configurable mediante variables de entorno

---

## Stack Tecnico

| Capa | Tecnologia | Version |
|------|------------|---------|
| Framework web | [FastAPI](https://fastapi.tiangolo.com) | `>= 0.115` |
| Servidor ASGI | [Uvicorn](https://www.uvicorn.org) | `>= 0.30` |
| Validacion | [Pydantic v2](https://docs.pydantic.dev) | `>= 2.9` |
| ORM | [SQLAlchemy async](https://docs.sqlalchemy.org) | `>= 2.0` |
| Base de datos (dev) | SQLite + aiosqlite | `>= 0.20` |
| Migraciones | [Alembic](https://alembic.sqlalchemy.org) | `>= 1.13` |
| Autenticacion | [python-jose](https://python-jose.readthedocs.io) | `>= 3.3` |
| Rate Limiting | [slowapi](https://github.com/laurentS/slowapi) | `>= 0.1.10` |
| Tests | [pytest-asyncio](https://pytest-asyncio.readthedocs.io) + [httpx](https://www.python-httpx.org) | `>= 8.3` |
| Linter / Formatter | [Ruff](https://docs.astral.sh/ruff) | `>= 0.6` |
| Tipado estatico | [mypy](https://mypy-lang.org) | `>= 1.11` |

---

## Arquitectura

```
+-----------------------------------------------------+
|                    HTTP / HTTPS                     |
+--------------------------+--------------------------+
                           |
+--------------------------v--------------------------+
|              app/api/v1/endpoints/                  |
|    usuarios.py | auth.py  <- Controladores HTTP     |
+--------------------------+--------------------------+
                           |  Inyecta
+--------------------------v--------------------------+
|              app/servicios/                         |
|           usuario.py  <- Logica de Negocio          |
+--------------------------+--------------------------+
                           |  Inyecta
+--------------------------v--------------------------+
|           app/repositorios/                         |
|     base.py + usuario.py  <- Acceso a Datos         |
+--------------------------+--------------------------+
                           |  Utiliza
+--------------------------v--------------------------+
|        app/modelos/ + app/db/                       |
|    SQLAlchemy ORM + Alembic Migraciones             |
+-----------------------------------------------------+
```

---

## Instalacion

### Requisitos previos

- Python 3.11+
- pip

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/alej-developer/clientevalidacion.git
cd clientevalidacion

# 2. Crear y activar entorno virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# 3. Instalar dependencias
pip install -e ".[dev]"

# 4. Configurar variables de entorno
cp .env.example .env

# 5. Ejecutar migraciones
python -m alembic upgrade head
```

---

## Variables de Entorno

Archivo `.env.example`:

```env
# Aplicacion
APP_NOMBRE="ClienteValidacion API"
APP_VERSION="0.2.0"
APP_DEBUG=false

# Base de datos
BD_URL="sqlite+aiosqlite:///./desarrollo.db"

# CORS
CORS_ORIGENES='["http://localhost:3000","http://localhost:5173"]'

# JWT
JWT_SECRETO="cambia-esto-en-produccion-con-un-secreto-fuerte-de-32-chars"
JWT_EXPIRACION_MINUTOS=60

# Rate Limiting
LIMITE_POR_DEFECTO="60/minute"
LIMITE_AUTH="10/minute"

# Logging
LOG_NIVEL="INFO"
```

---

## Ejecutar el Servidor

```bash
uvicorn app.main:app --reload --port 8000
```

Documentacion interactiva:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health Check: `http://localhost:8000/health`

---

## Endpoints de la API

### Sistema

| Metodo | Ruta | Descripcion | Autenticacion |
|--------|------|-------------|---------------|
| `GET` | `/health` | Estado del servicio y version | No |

### Autenticacion (`/api/v1/auth`)

| Metodo | Ruta | Descripcion | Autenticacion | Rate Limit |
|--------|------|-------------|---------------|------------|
| `POST` | `/api/v1/auth/login` | Login con credenciales -> Token JWT | No | 10/min |
| `GET` | `/api/v1/auth/yo` | Perfil del usuario autenticado | Si (Bearer) | 60/min |

### Usuarios (`/api/v1/usuarios`)

| Metodo | Ruta | Descripcion | Autenticacion |
|--------|------|-------------|---------------|
| `POST` | `/api/v1/usuarios` | Registrar nuevo usuario | No |
| `GET` | `/api/v1/usuarios` | Listar usuarios (paginacion, busqueda `q`, filtro `esta_activo`, orden) | No |
| `GET` | `/api/v1/usuarios/{id}` | Obtener detalle de usuario por UUID | No |
| `PATCH` | `/api/v1/usuarios/{id}` | Actualizacion parcial de datos | Si (Bearer) |
| `DELETE` | `/api/v1/usuarios/{id}` | Soft delete (borrado logico) | Si (Bearer) |
| `POST` | `/api/v1/usuarios/{id}/restaurar` | Restaurar usuario eliminado | Si (Bearer) |

---

## Autenticacion JWT

1. Registrar un usuario:
```bash
curl -X POST http://localhost:8000/api/v1/usuarios \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Usuario Ejemplo", "email": "usuario@ejemplo.com", "contrasena": "Password#123"}'
```

2. Obtener el token de acceso:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=usuario@ejemplo.com&password=Password#123"
```

3. Usar el token en cabecera `Authorization`:
```bash
curl -X GET http://localhost:8000/api/v1/auth/yo \
  -H "Authorization: Bearer <TOKEN_AQUI>"
```

---

## Rate Limiting

El sistema implementa limitacion de tasa mediante `slowapi`:
- **Autenticacion (`/api/v1/auth/login`)**: maximo 10 solicitudes por minuto por direccion IP.
- **Rutas generales**: maximo 60 solicitudes por minuto por defecto.
- Las solicitudes excedidas reciben codigo de estado `429 Too Many Requests`.

---

## Ejecutar Tests

```bash
# Todos los tests
pytest -v

# Con reporte de cobertura
pytest --cov=app --cov-report=term-missing
```

---

## Estructura del Proyecto

```
clientevalidacion/
|-- alembic/                  # Migraciones de base de datos
|   |-- env.py
|   `-- versions/
|-- app/
|   |-- api/
|   |   |-- deps.py           # Inyeccion de dependencias (DB, JWT)
|   |   `-- v1/
|   |       |-- endpoints/
|   |       |   |-- auth.py   # Autenticacion
|   |       |   `-- usuarios.py # Gestion de usuarios
|   |       `-- router.py
|   |-- core/
|   |   |-- config.py         # Configuracion y variables de entorno
|   |   |-- database.py       # Motor asincrono y sesion SQLAlchemy
|   |   |-- limiter.py        # Instancia de Rate Limiting
|   |   |-- logging.py        # Logging estructurado
|   |   |-- seguridad.py      # Generacion y verificacion de JWT
|   |   `-- excepciones/      # Excepciones de dominio y middleware
|   |-- db/
|   |   |-- base_class.py     # Clase base ORM (UUID, marcas temporales, soft delete)
|   |   `-- registro.py
|   |-- esquemas/             # Modelos de validacion Pydantic v2
|   |-- modelos/              # Modelos ORM SQLAlchemy
|   |-- repositorios/         # Capa de persistencia
|   |-- servicios/            # Logica de negocio
|   `-- main.py               # Instancia FastAPI y ciclo de vida
|-- tests/                    # Suite de pruebas automatizadas
|-- .env.example
|-- .gitignore
|-- alembic.ini
`-- pyproject.toml
```

---

## Licencia

Este proyecto esta bajo la Licencia MIT.
