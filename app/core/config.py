"""
Módulo de configuración centralizada de la aplicación.

Utiliza pydantic-settings para validar y tipar todas las variables
de entorno necesarias. Carga automáticamente desde el archivo .env.
"""

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    """Configuración global de la aplicación con validación estricta."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Aplicación ---
    app_nombre: str = "Mi API FastAPI"
    app_version: str = "0.1.0"
    app_descripcion: str = "API REST profesional con FastAPI"
    app_debug: bool = False

    # --- Base de datos ---
    bd_url: str = "sqlite+aiosqlite:///./desarrollo.db"
    bd_echo: bool = False

    # --- CORS ---
    cors_origenes: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # --- Logging ---
    log_nivel: str = "INFO"

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


@lru_cache(maxsize=1)
def obtener_configuracion() -> Configuracion:
    """
    Obtiene la instancia de configuración (singleton cacheada).

    Retorna:
        Instancia única de Configuracion con las variables de entorno cargadas.
    """
    return Configuracion()
