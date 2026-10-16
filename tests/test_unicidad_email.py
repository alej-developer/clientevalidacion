"""
Tests del índice único parcial de email (PR: unicidad a nivel de base de datos).

Verifica que la BD rechaza emails duplicados entre usuarios activos
(eliminado_en IS NULL), que el soft delete libera el email para
reutilizarlo, y que la carrera de creación se traduce en un 409
(ConflictoError) en vez de un 500.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excepciones.excepciones import ConflictoError
from app.esquemas.usuario import CrearUsuario
from app.modelos.usuario import Usuario
from app.servicios.usuario import ServicioUsuario


def _usuario(email: str, nombre: str = "Usuario Prueba") -> Usuario:
    """Construye una instancia de Usuario lista para insertar en tests."""
    return Usuario(
        id=uuid.uuid4(),
        nombre=nombre,
        email=email,
        contrasena_hash="salt:hash",
        esta_activo=True,
    )


async def test_email_duplicado_entre_activos_falla_en_bd(sesion_db: AsyncSession) -> None:
    """Dos usuarios activos con el mismo email violan el índice único parcial."""
    sesion_db.add(_usuario("duplicado@ejemplo.com"))
    await sesion_db.commit()

    sesion_db.add(_usuario("duplicado@ejemplo.com", nombre="Otro Usuario"))
    with pytest.raises(IntegrityError):
        await sesion_db.commit()
    await sesion_db.rollback()


async def test_email_reutilizable_tras_soft_delete(sesion_db: AsyncSession) -> None:
    """El email de un usuario eliminado (soft) queda libre para reutilizarlo."""
    original = _usuario("liberado@ejemplo.com")
    sesion_db.add(original)
    await sesion_db.commit()

    original.eliminado_en = datetime.now(tz=UTC)
    await sesion_db.commit()

    sesion_db.add(_usuario("liberado@ejemplo.com", nombre="Nuevo Usuario"))
    await sesion_db.commit()  # No debe lanzar


async def test_varios_eliminados_pueden_compartir_email(sesion_db: AsyncSession) -> None:
    """Varios registros eliminados pueden compartir email (histórico permitido)."""
    ahora = datetime.now(tz=UTC)
    eliminado_1 = _usuario("historico@ejemplo.com")
    eliminado_1.eliminado_en = ahora
    eliminado_2 = _usuario("historico@ejemplo.com", nombre="Otro Eliminado")
    eliminado_2.eliminado_en = ahora
    sesion_db.add_all([eliminado_1, eliminado_2])
    await sesion_db.commit()  # No debe lanzar


async def test_carrera_de_creacion_se_traduce_a_conflicto(
    sesion_db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Si otro request crea el mismo email entre existe_email y el flush,
    el IntegrityError de la BD se traduce a ConflictoError (409), no a un 500.
    """
    servicio = ServicioUsuario(sesion=sesion_db)
    datos = CrearUsuario(
        nombre="Usuario Carrera",
        email="carrera@ejemplo.com",
        contrasena="Password#123",
    )
    await servicio.crear_usuario(datos)

    async def _existe_email_falso(email: str) -> bool:
        return False

    monkeypatch.setattr(servicio._repositorio, "existe_email", _existe_email_falso)
    with pytest.raises(ConflictoError):
        await servicio.crear_usuario(datos)
