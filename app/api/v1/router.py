from fastapi import APIRouter

from app.api.v1.endpoints import auth, usuarios

api_v1_router = APIRouter(prefix="/api/v1")

# Registrar sub-routers
api_v1_router.include_router(usuarios.router)
api_v1_router.include_router(auth.router)
