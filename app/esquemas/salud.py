"""
Esquema de respuesta para el endpoint de salud (/health).
"""

from datetime import datetime

from pydantic import BaseModel, Field


class RespuestaSalud(BaseModel):
    """Esquema de respuesta del endpoint de verificación de salud."""

    estado: str = Field(
        default="ok",
        description="Estado actual del servicio",
        examples=["ok"],
    )
    version: str = Field(
        description="Versión actual de la aplicación",
        examples=["0.1.0"],
    )
    timestamp: datetime = Field(
        description="Marca de tiempo de la respuesta en formato ISO 8601",
    )
    nombre_app: str = Field(
        description="Nombre de la aplicación",
        examples=["Mi API FastAPI"],
    )
