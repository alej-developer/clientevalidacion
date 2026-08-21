"""
Configuración del entorno de ejecución de Alembic para migraciones asíncronas.

Conecta Alembic con la configuración de la aplicación (pydantic-settings)
y registra automáticamente todos los modelos para la autogeneración
de migraciones.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import obtener_configuracion
from app.db.registro import ModeloBase  # Importa base + todos los modelos registrados

# Configuración de Alembic leída desde alembic.ini
config = context.config

# Interpretar el archivo de configuración de logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inyectar la URL de base de datos desde nuestra configuración centralizada
_app_config = obtener_configuracion()
config.set_main_option("sqlalchemy.url", _app_config.bd_url)

# Metadatos del modelo base para la autogeneración de migraciones
target_metadata = ModeloBase.metadata


def ejecutar_migraciones_offline() -> None:
    """
    Ejecuta las migraciones en modo 'offline' (solo genera SQL).

    Configura el contexto con la URL directamente, sin necesidad
    de crear una conexión al motor de base de datos.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def ejecutar_migraciones_con_conexion(connection: Connection) -> None:
    """
    Configura y ejecuta las migraciones usando una conexión activa.

    Args:
        connection: Conexión síncrona de SQLAlchemy para ejecutar las migraciones.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def ejecutar_migraciones_async() -> None:
    """
    Ejecuta las migraciones en modo 'online' asíncrono.

    Crea un motor asíncrono desde la configuración de Alembic,
    obtiene una conexión y ejecuta las migraciones de forma síncrona
    dentro del contexto de la conexión.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(ejecutar_migraciones_con_conexion)

    await connectable.dispose()


if context.is_offline_mode():
    ejecutar_migraciones_offline()
else:
    asyncio.run(ejecutar_migraciones_async())
