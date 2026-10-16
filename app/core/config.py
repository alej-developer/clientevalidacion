"""
Módulo de configuración centralizada de la aplicación.

Utiliza pydantic-settings para validar y tipar todas las variables
de entorno necesarias. Carga automáticamente desde el archivo .env.
"""

from functools import lru_cache
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valor por defecto del secreto JWT (público, solo válido en desarrollo)
JWT_SECRETO_POR_DEFECTO = "cambia-esto-en-produccion-con-un-secreto-fuerte-de-32-chars"


class Configuracion(BaseSettings):
    """Configuración global de la aplicación con validación estricta."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Aplicación ---
    app_nombre: str = "ClienteValidacion API"
    app_version: str = "0.2.0"
    app_descripcion: str = (
        "## ClienteValidacion - API REST profesional con FastAPI\n\n"
        "Gestion de usuarios con autenticacion JWT, soft delete y rate limiting.\n\n"
        "### Caracteristicas\n"
        "- Autenticacion JWT con python-jose\n"
        "- Soft Delete con restauracion de registros\n"
        "- Paginacion, ordenacion y filtros de busqueda avanzada\n"
        "- Rate Limiting con slowapi\n"
        "- Arquitectura limpia en capas\n"
        "- Migraciones asincronas con Alembic\n"
    )
    app_debug: bool = False

    # --- Rate Limiting ---
    limite_por_defecto: str = "60/minute"
    limite_auth: str = "10/minute"

    # --- Base de datos ---
    bd_url: str = "sqlite+aiosqlite:///./desarrollo.db"
    bd_echo: bool = False

    # --- CORS ---
    cors_origenes: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # --- JWT ---
    jwt_secreto: str = JWT_SECRETO_POR_DEFECTO

    jwt_expiracion_minutos: int = 60

    # --- Cookie de autenticación ---
    # None = automático: segura (Secure) salvo en desarrollo (APP_DEBUG=true,
    # donde http://localhost no acepta cookies Secure).
    cookie_segura: bool | None = None

    # --- Logging ---
    log_nivel: str = "INFO"

    @model_validator(mode="after")
    def validar_secreto_jwt_en_produccion(self) -> "Configuracion":
        """
        Impide arrancar en modo producción con el secreto JWT por defecto.

        El valor por defecto es público (está en el repositorio): con
        APP_DEBUG=false cualquiera podría firmar tokens válidos. En
        desarrollo (APP_DEBUG=true) se permite para no pedir .env.
        """
        if not self.app_debug and self.jwt_secreto == JWT_SECRETO_POR_DEFECTO:
            msg = (
                "JWT_SECRETO tiene el valor por defecto (público) y APP_DEBUG=false. "
                "Define un secreto fuerte en .env antes de arrancar en producción."
            )
            raise ValueError(msg)
        return self

    @field_validator("log_nivel")
    @classmethod
    def validar_nivel_log(cls, valor: str) -> str:
        """Valida que el nivel de log sea uno de los permitidos."""
        niveles_permitidos = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        valor_upper = valor.upper()
        if valor_upper not in niveles_permitidos:
            msg = (
                f"Nivel de log '{valor}' no válido. "
                f"Opciones: {', '.join(sorted(niveles_permitidos))}"
            )
            raise ValueError(msg)
        return valor_upper

    @field_validator("cors_origenes", mode="before")
    @classmethod
    def parsear_origenes_cors(cls, valor: Any) -> list[str]:
        """Convierte una cadena JSON de orígenes CORS a lista."""
        if isinstance(valor, str):
            import json

            try:
                resultado = json.loads(valor)
                if isinstance(resultado, list):
                    return [str(item) for item in resultado]
            except json.JSONDecodeError:
                # Si no es JSON, tratar como lista separada por comas
                return [origen.strip() for origen in valor.split(",") if origen.strip()]
        if isinstance(valor, list):
            return [str(item) for item in valor]
        return [str(valor)]


def _cookie_segura_efectiva(config: "Configuracion") -> bool:
    """Resuelve si la cookie de auth lleva el flag Secure."""
    if config.cookie_segura is not None:
        return config.cookie_segura
    return not config.app_debug


@lru_cache(maxsize=1)
def obtener_configuracion() -> Configuracion:
    """
    Obtiene la instancia de configuración (singleton cacheada).

    Retorna:
        Instancia única de Configuracion con las variables de entorno cargadas.
    """
    return Configuracion()
