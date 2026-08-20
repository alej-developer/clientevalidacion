"""
Módulo de conexión y gestión de sesiones asíncronas de base de datos.

Configura el motor asíncrono con pooling, la fábrica de sesiones y el
generador de dependencias para inyección en los endpoints de FastAPI.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import obtener_configuracion
from app.core.logging import obtener_logger

_logger = obtener_logger("database")
_config = obtener_configuracion()

# --- Motor asíncrono con pooling configurado ---
motor_asincrono = create_async_engine(
    url=_config.bd_url,
    echo=_config.bd_echo,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
)

# --- Fábrica de sesiones asíncronas ---
fabrica_sesiones = async_sessionmaker(
    bind=motor_asincrono,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def obtener_db() -> AsyncIterator[AsyncSession]:
    """
    Generador de dependencias que proporciona una sesión de base de datos.

    Gestiona automáticamente el ciclo de vida de la sesión:
    - Hace commit si la operación es exitosa.
    - Hace rollback ante cualquier excepción.
    - Cierra la sesión al finalizar, independientemente del resultado.

    Yields:
        Sesión asíncrona de SQLAlchemy configurada y lista para usar.

    Raises:
        Exception: Re-lanza cualquier excepción tras hacer rollback.
    """
    sesion = fabrica_sesiones()
    try:
        yield sesion
        await sesion.commit()
        _logger.debug("Sesión de base de datos comprometida correctamente.")
    except Exception:
        await sesion.rollback()
        _logger.error("Error en la sesión — rollback ejecutado.", exc_info=True)
        raise
    finally:
        await sesion.close()
        _logger.debug("Sesión de base de datos cerrada.")
