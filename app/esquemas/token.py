"""
Esquemas Pydantic para la respuesta y payload de tokens JWT.
"""

import uuid

from pydantic import BaseModel, Field


class Token(BaseModel):
    """Respuesta del endpoint de login con el token de acceso."""

    access_token: str = Field(description="JWT de acceso firmado")
    token_type: str = Field(default="bearer", description="Tipo de token (siempre 'bearer')")
    expira_en: int = Field(description="Tiempo de expiración en segundos")


class TokenPayload(BaseModel):
    """Payload interno del JWT decodificado."""

    sub: uuid.UUID = Field(description="UUID del usuario autenticado")
    tipo: str = Field(default="access", description="Tipo de token")
