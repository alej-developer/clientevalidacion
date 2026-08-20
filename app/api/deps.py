"""
Inyección de dependencias para los endpoints de la API.

Proporciona funciones generadoras de dependencias para instanciar
servicios de negocio inyectando la sesión de base de datos asíncrona.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import obtener_db
from app.servicios.usuario import ServicioUsuario


def obtener_servicio_usuario(
    sesion: Annotated[AsyncSession, Depends(obtener_db)],
) -> ServicioUsuario:
    """
    Inyecta una instancia de ServicioUsuario configurada con la sesión actual.

    Args:
        sesion: Sesión asíncrona de base de datos inyectada por FastAPI.

    Retorna:
        Instancia de ServicioUsuario lista para procesar la lógica de negocio.
    """
    return ServicioUsuario(sesion=sesion)
