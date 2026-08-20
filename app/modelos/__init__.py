"""
Paquete de modelos SQLAlchemy (entidades de base de datos).

Importa todos los modelos para que Alembic y la clase base
los detecten automáticamente al generar migraciones.
"""

from app.modelos.usuario import Usuario

__all__ = ["Usuario"]
