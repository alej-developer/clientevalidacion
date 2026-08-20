"""
Modelo de dominio: Usuario.

Representa un usuario registrado en el sistema con sus datos de perfil
y credenciales. Aplica tipado estricto de SQLAlchemy 2.0 con índices
y restricciones únicas.
"""

from sqlalchemy import Index, String
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
        unique=True,
        index=True,
        doc="Dirección de correo electrónico única del usuario",
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

    # --- Índices compuestos ---
    __table_args__ = (
        Index("ix_usuarios_email_activo", "email", "esta_activo"),
        {"comment": "Tabla de usuarios registrados en el sistema"},
    )

    def __repr__(self) -> str:
        """Representación legible del usuario para depuración."""
        return f"<Usuario(id={self.id}, email='{self.email}', activo={self.esta_activo})>"
