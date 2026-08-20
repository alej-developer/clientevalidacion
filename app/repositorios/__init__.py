"""
Paquete de repositorios (acceso a datos).

Exporta los repositorios disponibles para inyección de dependencias.
"""

from app.repositorios.base import RepositorioBase
from app.repositorios.usuario import RepositorioUsuario

__all__ = ["RepositorioBase", "RepositorioUsuario"]
