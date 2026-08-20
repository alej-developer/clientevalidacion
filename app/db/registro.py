"""
Registro centralizado de todos los modelos ORM.

Este módulo importa ModeloBase y todos los modelos para que Alembic
pueda detectar automáticamente las tablas al generar migraciones.
Cualquier modelo nuevo debe importarse aquí.

IMPORTANTE: No importar este módulo desde los propios modelos
para evitar importaciones circulares. Solo usar desde Alembic (env.py)
y scripts que necesiten acceso al metadata completo.
"""

from app.db.base_class import ModeloBase
from app.modelos.usuario import Usuario

__all__ = ["ModeloBase", "Usuario"]
