"""
Esquemas Pydantic para la respuesta y payload de tokens JWT.
"""

import uuid

from pydantic import BaseModel, Field


class Token(BaseModel):
    """Respuesta del endpoint de login con el token de acceso."""

    access_token: str = Field(description="JWT de acceso firmado")
    refresh_token: str = Field(description="Refresh token opaco para renovar el acceso")
    token_type: str = Field(default="bearer", description="Tipo de token (siempre 'bearer')")
    expira_en: int = Field(description="Tiempo de expiración en segundos")


class PeticionRefresh(BaseModel):
    """Cuerpo opcional de POST /auth/refresh (alternativa a la cookie httpOnly)."""

    refresh_token: str | None = Field(
        default=None,
        description="Refresh token en claro; si falta, se lee de la cookie httpOnly",
    )


class TokenPayload(BaseModel):
    """Payload interno del JWT decodificado."""

    sub: uuid.UUID = Field(description="UUID del usuario autenticado")
    tipo: str = Field(default="access", description="Tipo de token")
