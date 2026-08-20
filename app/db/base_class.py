"""
Clase base declarativa para todos los modelos SQLAlchemy.

Proporciona campos de auditoría automáticos (id UUID, creado_en,
actualizado_en) que heredan todos los modelos de la aplicación.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ModeloBase(DeclarativeBase):
    """
    Clase base abstracta para todos los modelos ORM.

    Incluye automáticamente:
        - id: Clave primaria UUID v4 generada automáticamente.
        - creado_en: Marca temporal de creación (UTC), asignada por el servidor.
        - actualizado_en: Marca temporal de última actualización (UTC), actualizada automáticamente.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        doc="Identificador único universal del registro",
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        server_default=func.now(),
        nullable=False,
        doc="Fecha y hora de creación del registro (UTC)",
    )

    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(tz=UTC),
        nullable=False,
        doc="Fecha y hora de la última actualización del registro (UTC)",
    )

    def __repr__(self) -> str:
        """Representación legible del modelo para depuración."""
        return f"<{self.__class__.__name__}(id={self.id})>"
