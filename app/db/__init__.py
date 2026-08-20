"""
Paquete de base de datos: clase base declarativa y utilidades.

Para registrar todos los modelos (necesario para Alembic), importar
desde app.db.registro en vez de este __init__.
"""

from app.db.base_class import ModeloBase

__all__ = ["ModeloBase"]
