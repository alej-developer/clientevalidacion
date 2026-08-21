<div align="center">

# 🚀 FastAPI — API REST Profesional

**API REST de gestión de usuarios construida con FastAPI, arquitectura limpia y Domain-Driven Design simplificado.**

[![Tests](https://img.shields.io/badge/tests-26%20passed-brightgreen?style=flat-square&logo=pytest)](https://github.com/alej-developer/clientevalidacion)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square&logo=python)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%20async-red?style=flat-square)](https://www.sqlalchemy.org)
[![License](https://img.shields.io/badge/license-MIT-informational?style=flat-square)](LICENSE)

</div>

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Stack Técnico](#-stack-técnico)
- [Arquitectura](#-arquitectura)
- [Instalación](#-instalación)
- [Variables de Entorno](#-variables-de-entorno)
- [Ejecutar el Servidor](#-ejecutar-el-servidor)
- [Endpoints de la API](#-endpoints-de-la-api)
- [Autenticación JWT](#-autenticación-jwt)
- [Ejecutar Tests](#-ejecutar-tests)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Contribuir](#-contribuir)

---

## ✨ Características

- ✅ **CRUD completo** de usuarios con validaciones estrictas (email, contraseña)
- 🔐 **Autenticación JWT** con `python-jose` — endpoints protegidos con `Bearer` token
- 🗑️ **Soft Delete inteligente** — borrado lógico con restauración, sin pérdida de datos
- 📧 **Reutilización de email** tras soft delete (constraint compuesta `email + eliminado_en`)
- 📄 **Paginación** y filtros por estado activo
- 🏗️ **Arquitectura limpia** — Core → DB → Domain → API con capas bien separadas
- 🔄 **Migraciones Alembic** versionadas con soporte asíncrono
- 🧪 **26 tests de integración** con base de datos en memoria aislada por test
- 📚 **OpenAPI/Swagger UI** enriquecida con descripción, tags y ejemplos
- 📝 **Logging estructurado** configurable por nivel
- 🌐 **CORS** configurable desde variables de entorno

---

## 🛠 Stack Técnico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Framework web | [FastAPI](https://fastapi.tiangolo.com) | `≥ 0.115` |
| Servidor ASGI | [Uvicorn](https://www.uvicorn.org) | `≥ 0.30` |
| Validación | [Pydantic v2](https://docs.pydantic.dev) | `≥ 2.9` |
| ORM | [SQLAlchemy async](https://docs.sqlalchemy.org) | `≥ 2.0` |
| Base de datos (dev) | SQLite + aiosqlite | `≥ 0.20` |
| Migraciones | [Alembic](https://alembic.sqlalchemy.org) | `≥ 1.13` |
| Autenticación | [python-jose](https://python-jose.readthedocs.io) | `≥ 3.3` |
| Tests | [pytest-asyncio](https://pytest-asyncio.readthedocs.io) + [httpx](https://www.python-httpx.org) | `≥ 8.3` |
| Linting | [Ruff](https://docs.astral.sh/ruff) | `≥ 0.6` |
| Tipos | [mypy](https://mypy-lang.org) | `≥ 1.11` |

---

## 🏛 Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                    HTTP / HTTPS                     │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│              app/api/v1/endpoints/                  │
│   usuarios.py │ auth.py  ←  Controladores HTTP      │
└─────────────────┬───────────────────────────────────┘
                  │  Depende de
┌─────────────────▼───────────────────────────────────┐
│              app/servicios/                         │
│          usuario.py  ←  Lógica de Negocio           │
└─────────────────┬───────────────────────────────────┘
                  │  Depende de
┌─────────────────▼───────────────────────────────────┐
│           app/repositorios/                         │
│    base.py + usuario.py  ←  Acceso a Datos          │
└─────────────────┬───────────────────────────────────┘
                  │  Depende de
┌─────────────────▼───────────────────────────────────┐
│        app/modelos/ + app/db/                       │
│    SQLAlchemy ORM + Alembic Migraciones             │
└─────────────────────────────────────────────────────┘
```

**Capas transversales** (`app/core/`): configuración, logging, seguridad JWT, excepciones y middlewares.

---

## 🚀 Instalación

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
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

# 3. Instalar dependencias
pip install -e ".[dev]"

# 4. Copiar el archivo de entorno
cp .env.example .env
# Edita .env con tus valores (especialmente JWT_SECRETO)

# 5. Ejecutar las migraciones
python -m alembic upgrade head
```

---

## ⚙️ Variables de Entorno

Copia `.env.example` a `.env` y ajusta los valores:

```env
# === Aplicación ===
APP_NOMBRE="ClienteValidacion API"
APP_VERSION="0.1.0"
APP_DEBUG=false

# === Base de Datos ===
BD_URL="sqlite+aiosqlite:///./desarrollo.db"
# Para PostgreSQL:
# BD_URL="postgresql+asyncpg://user:password@localhost:5432/dbname"

# === CORS ===
CORS_ORIGENES='["http://localhost:3000","http://localhost:5173"]'

# === JWT ===
# ¡CAMBIA esto en producción! Genera con: openssl rand -hex 32
JWT_SECRETO="cambia-esto-en-produccion-con-un-secreto-fuerte-de-32-chars"
JWT_EXPIRACION_MINUTOS=60

# === Logging ===
LOG_NIVEL="INFO"  # DEBUG | INFO | WARNING | ERROR | CRITICAL
```

> ⚠️ **Importante:** Nunca subas tu `.env` real al repositorio. Está incluido en `.gitignore`.

---

## ▶️ Ejecutar el Servidor

```bash
# Modo desarrollo (con recarga automática)
uvicorn app.main:app --reload --port 8000

# La documentación interactiva estará disponible en:
# Swagger UI  →  http://localhost:8000/docs
# ReDoc       →  http://localhost:8000/redoc
# OpenAPI JSON → http://localhost:8000/openapi.json
# Health Check → http://localhost:8000/health
```

---

## 📡 Endpoints de la API

### Sistema

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| `GET` | `/health` | Estado del servicio | ❌ |

### Autenticación (`/api/v1/auth`)

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| `POST` | `/api/v1/auth/login` | Login con email + contraseña → JWT | ❌ |
| `GET` | `/api/v1/auth/yo` | Perfil del usuario autenticado | ✅ |

### Usuarios (`/api/v1/usuarios`)

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| `POST` | `/api/v1/usuarios` | Crear nuevo usuario | ❌ |
| `GET` | `/api/v1/usuarios` | Listar usuarios (paginado) | ❌ |
| `GET` | `/api/v1/usuarios/{id}` | Obtener usuario por UUID | ❌ |
| `PATCH` | `/api/v1/usuarios/{id}` | Actualizar parcialmente | ✅ |
| `DELETE` | `/api/v1/usuarios/{id}` | Soft delete | ✅ |
| `POST` | `/api/v1/usuarios/{id}/restaurar` | Restaurar usuario eliminado | ✅ |

---

## 🔐 Autenticación JWT

La API usa **OAuth2 con JWT Bearer tokens**. Para autenticarte:

### 1. Registra un usuario
```bash
curl -X POST http://localhost:8000/api/v1/usuarios \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Juan García", "email": "juan@ejemplo.com", "contrasena": "MiPass#123"}'
```

### 2. Obtén el token
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=juan@ejemplo.com&password=MiPass#123"

# Respuesta:
# {"access_token": "eyJ...", "token_type": "bearer", "expira_en": 3600}
```

### 3. Usa el token en las peticiones protegidas
```bash
curl -X DELETE http://localhost:8000/api/v1/usuarios/{uuid} \
  -H "Authorization: Bearer eyJ..."
```

> 💡 En **Swagger UI** (`/docs`), usa el botón **🔒 Authorize** para introducir el token de forma cómoda.

---

## 🧪 Ejecutar Tests

```bash
# Todos los tests
pytest -v

# Solo una suite específica
pytest tests/test_auth.py -v
pytest tests/test_soft_delete.py -v

# Con cobertura (requiere pytest-cov)
pytest --cov=app --cov-report=term-missing
```

Los tests usan **SQLite en memoria**, aislada por cada test mediante fixtures de `conftest.py`. No afectan a la base de datos de desarrollo.

**Suite actual:**

| Archivo | Tests | Descripción |
|---------|-------|-------------|
| `test_api.py` | 9 | CRUD completo de usuarios |
| `test_auth.py` | 10 | Login, JWT, endpoints protegidos |
| `test_soft_delete.py` | 7 | Soft delete, restauración, reutilización de email |
| **Total** | **26** | **100% passing ✅** |

---

## 📁 Estructura del Proyecto

```
clientevalidacion/
├── alembic/                  # Migraciones de base de datos
│   ├── env.py                # Entorno Alembic asíncrono
│   └── versions/             # Historial de migraciones
├── app/
│   ├── api/
│   │   ├── deps.py           # Inyección de dependencias (DB, JWT)
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── auth.py   # POST /login, GET /yo
│   │       │   └── usuarios.py # CRUD + restaurar
│   │       └── router.py     # Router principal v1
│   ├── core/
│   │   ├── config.py         # Variables de entorno (Pydantic Settings)
│   │   ├── database.py       # Motor y sesión SQLAlchemy async
│   │   ├── logging.py        # Logging estructurado
│   │   ├── seguridad.py      # JWT: crear/decodificar tokens
│   │   └── excepciones/      # Excepciones de dominio + middleware
│   ├── db/
│   │   ├── base_class.py     # ModeloBase (id, creado_en, eliminado_en...)
│   │   └── registro.py       # Importación de modelos para Alembic
│   ├── esquemas/
│   │   ├── token.py          # Token, TokenPayload
│   │   ├── usuario.py        # CrearUsuario, ActualizarUsuario, RespuestaUsuario
│   │   └── salud.py          # RespuestaSalud
│   ├── modelos/
│   │   └── usuario.py        # Modelo ORM Usuario
│   ├── repositorios/
│   │   ├── base.py           # CRUD genérico + soft delete
│   │   └── usuario.py        # Repositorio especializado
│   ├── servicios/
│   │   └── usuario.py        # Lógica de negocio + hash contraseñas
│   └── main.py               # Punto de entrada FastAPI
├── tests/
│   ├── conftest.py           # Fixtures: DB en memoria, cliente async
│   ├── test_api.py           # Tests CRUD
│   ├── test_auth.py          # Tests autenticación JWT
│   └── test_soft_delete.py   # Tests soft delete
├── .env.example              # Plantilla de variables de entorno
├── .gitignore
├── alembic.ini
└── pyproject.toml            # Dependencias, herramientas (ruff, mypy, pytest)
```

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Consulta la [guía de contribución](.github/CONTRIBUTING.md) para más detalles.

---

<div align="center">

Hecho con ❤️ usando [FastAPI](https://fastapi.tiangolo.com)

</div>
