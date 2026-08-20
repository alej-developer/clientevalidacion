"""
Paquete de servicios (lógica de negocio).

Exporta los servicios disponibles para inyección de dependencias.
"""

from app.servicios.usuario import ServicioUsuario

__all__ = ["ServicioUsuario"]
