"""
Modelo de dominio: Usuario.

Representa un usuario registrado en el sistema con sus datos de perfil
y credenciales. Aplica tipado estricto de SQLAlchemy 2.0 con índices
y restricciones únicas.
"""

from sqlalchemy import Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import ModeloBase


class Usuario(ModeloBase):
    """
    Entidad de dominio que representa un usuario del sistema.

    Atributos:
        nombre: Nombre completo del usuario.
        email: Dirección de correo electrónico (única, indexada).
        contrasena_hash: Hash de la contraseña almacenada de forma segura.
        esta_activo: Indica si la cuenta del usuario está habilitada.
    """

    __tablename__ = "usuarios"

    nombre: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        doc="Nombre completo del usuario",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Dirección de correo electrónico del usuario",
    )

    contrasena_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Hash bcrypt de la contraseña del usuario",
    )

    esta_activo: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        doc="Indica si la cuenta del usuario está activa",
    )

    # --- Índices y restricciones ---
    __table_args__ = (
        # Email único solo entre usuarios NO eliminados (índice único parcial).
        # Una constraint UNIQUE(email, eliminado_en) NO sirve: en SQL NULL != NULL,
        # así que permitía emails duplicados entre usuarios activos.
        # Usuarios con soft delete pueden liberar su email para reutilizarlo.
        Index(
            "ux_usuarios_email_activo",
            "email",
            unique=True,
            sqlite_where=text("eliminado_en IS NULL"),
            postgresql_where=text("eliminado_en IS NULL"),
        ),
        Index("ix_usuarios_email_activo", "email", "esta_activo"),
        {"comment": "Tabla de usuarios registrados en el sistema"},
    )

    def __repr__(self) -> str:
        """Representación legible del usuario para depuración."""
        return f"<Usuario(id={self.id}, email='{self.email}', activo={self.esta_activo})>"
