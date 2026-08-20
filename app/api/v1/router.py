"""
Router principal de la API v1.

Agrupa todos los sub-routers de los diferentes módulos
bajo el prefijo /api/v1.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import usuarios

api_v1_router = APIRouter(prefix="/api/v1")

# Registrar sub-routers
api_v1_router.include_router(usuarios.router)
