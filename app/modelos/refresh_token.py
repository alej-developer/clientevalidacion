"""
Modelo de dominio: RefreshToken.

Representa un refresh token opaco emitido en el login. Solo se almacena
su hash SHA-256 (nunca el valor en claro), lo que permite revocarlo y
limita el impacto de una fuga de la base de datos. La rotación marca el
token usado como revocado y enlaza con su reemplazo.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import ModeloBase


class RefreshToken(ModeloBase):
    """
    Refresh token persistente con revocación y rotación.

    Atributos:
        usuario_id: Usuario dueño del token.
        token_hash: Hash SHA-256 del token en claro (único).
        expira_en: Fecha de expiración absoluta del token (UTC).
        revocado: True si el token fue rotado o revocado (logout).
        reemplazado_por: ID del token que lo sustituyó al rotar, si aplica.
    """

    __tablename__ = "refresh_tokens"

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Usuario dueño del token",
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        doc="Hash SHA-256 del refresh token (nunca se guarda en claro)",
    )

    expira_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Fecha de expiración absoluta del token (UTC)",
    )

    revocado: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        doc="True si el token fue rotado o revocado",
    )

    reemplazado_por: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
        default=None,
        doc="ID del refresh token que lo reemplazó en la rotación",
    )

    def __repr__(self) -> str:
        """Representación legible del token para depuración (sin datos sensibles)."""
        return (
            f"<RefreshToken(id={self.id}, usuario_id={self.usuario_id}, revocado={self.revocado})>"
        )
