"""
Punto de entrada principal de la aplicación FastAPI.

Configura la instancia de FastAPI con:
- Ciclo de vida (lifespan) para inicialización y limpieza.
- Middleware CORS parametrizado desde la configuración.
- Middleware de captura global de excepciones.
- Gestión del motor de base de datos asíncrono.
- Endpoint de salud (/health).
- Metadatos OpenAPI enriquecidos (tags, contacto, licencia).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import obtener_configuracion
from app.core.database import motor_asincrono
from app.core.excepciones.middleware import MiddlewareExcepciones
from app.core.logging import configurar_logging, obtener_logger
from app.esquemas.salud import RespuestaSalud

_config = obtener_configuracion()
_logger = obtener_logger("main")

# --- Metadatos de tags para la documentación OpenAPI ---
_OPENAPI_TAGS = [
    {
        "name": "Sistema",
        "description": (
            "Endpoints de operación del sistema. Incluye el **health check** "
            "para verificar que el servicio está en línea y su versión actual."
        ),
    },
    {
        "name": "Autenticación",
        "description": (
            "Gestión de sesiones mediante **JWT Bearer tokens**. "
            "Usa `POST /login` para obtener un token y `GET /yo` para verificar "
            "la identidad del usuario autenticado. "
            "El token se envía en la cabecera: `Authorization: Bearer <token>`"
        ),
    },
    {
        "name": "Usuarios",
        "description": (
            "CRUD completo de usuarios con **soft delete** y restauración. "
            "Las operaciones de escritura (PATCH, DELETE, restaurar) requieren "
            "autenticación JWT. Los usuarios eliminados no se borran físicamente "
            "y pueden recuperarse con el endpoint `/restaurar`."
        ),
    },
]


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
    """
    Gestiona el ciclo de vida de la aplicación.

    Ejecuta lógica de inicialización al arrancar y de limpieza al detenerse.
    Incluye la gestión del motor de base de datos asíncrono.

    Args:
        app: Instancia de la aplicación FastAPI.
    """
    # --- Inicio ---
    configurar_logging(nivel=_config.log_nivel, es_debug=_config.app_debug)
    _logger.info(
        "Aplicación '%s' v%s iniciando...",
        _config.app_nombre,
        _config.app_version,
    )
    _logger.info("Motor de base de datos configurado: %s", _config.bd_url)
    yield
    # --- Cierre ---
    await motor_asincrono.dispose()
    _logger.info("Motor de base de datos cerrado.")
    _logger.info("Aplicación detenida correctamente.")


app = FastAPI(
    title=_config.app_nombre,
    version=_config.app_version,
    description=_config.app_descripcion,
    summary="API REST profesional de gestión de usuarios con autenticación JWT y soft delete.",
    debug=_config.app_debug,
    lifespan=ciclo_de_vida,
    openapi_tags=_OPENAPI_TAGS,
    contact={
        "name": "Alejandro — alej-developer",
        "url": "https://github.com/alej-developer/clientevalidacion",
        "email": "alejandropm32@gmail.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- Middleware de excepciones globales ---
app.add_middleware(MiddlewareExcepciones)

# --- Middleware CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=_config.cors_origenes,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers de la API ---
app.include_router(api_v1_router)


# --- Endpoint de salud ---
@app.get(
    "/health",
    response_model=RespuestaSalud,
    tags=["Sistema"],
    summary="Verificación de salud del servicio",
    description=(
        "Retorna el estado operativo actual del servicio, su versión y "
        "la marca de tiempo del servidor. Útil para health checks de "
        "balanceadores de carga y sistemas de monitoreo."
    ),
)
async def verificar_salud() -> RespuestaSalud:
    """Retorna el estado de salud actual de la aplicación."""
    return RespuestaSalud(
        estado="ok",
        version=_config.app_version,
        timestamp=datetime.now(tz=UTC),
        nombre_app=_config.app_nombre,
    )
