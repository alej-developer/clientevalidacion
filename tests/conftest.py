"""
Configuración de fixtures para pruebas de integración con pytest.

Proporciona la infraestructura de pruebas con:
- Base de datos SQLite asíncrona en memoria aislada por cada test.
- Sobrescritura de la dependencia obtener_db de FastAPI.
- Cliente HTTP asíncrono (httpx.AsyncClient) para realizar peticiones de prueba.
"""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.database import obtener_db
from app.db.registro import ModeloBase
from app.main import app

# Motor de base de datos en memoria para pruebas
MOTOR_PRUEBAS = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
)

# Fábrica de sesiones para pruebas
FabricaSesionesPruebas = async_sessionmaker(
    bind=MOTOR_PRUEBAS,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest.fixture(autouse=True)
async def preparar_base_datos() -> AsyncIterator[None]:
    """
    Crea las tablas en la base de datos en memoria antes de cada test
    y las destruye al finalizar para garantizar aislamiento total.
    """
    async with MOTOR_PRUEBAS.begin() as conexion:
        await conexion.run_sync(ModeloBase.metadata.create_all)

    yield

    async with MOTOR_PRUEBAS.begin() as conexion:
        await conexion.run_sync(ModeloBase.metadata.drop_all)


@pytest.fixture
async def sesion_db() -> AsyncIterator[AsyncSession]:
    """
    Proporciona una sesión de base de datos asíncrona para pruebas.

    Yields:
        AsyncSession conectada a la base de datos en memoria.
    """
    async with FabricaSesionesPruebas() as sesion:
        yield sesion


@pytest.fixture
async def cliente_async(sesion_db: AsyncSession) -> AsyncIterator[AsyncClient]:
    """
    Cliente HTTP asíncrono para interactuar con la API FastAPI en los tests.

    Sobrescribe la dependencia `obtener_db` para que la aplicación
    utilice la sesión de pruebas en memoria.

    Yields:
        httpx.AsyncClient configurado con la aplicación FastAPI.
    """

    async def _obtener_db_prueba() -> AsyncIterator[AsyncSession]:
        yield sesion_db

    app.dependency_overrides[obtener_db] = _obtener_db_prueba

    transporte = ASGITransport(app=app)
    async with AsyncClient(transport=transporte, base_url="http://test") as cliente:
        yield cliente

    app.dependency_overrides.clear()
