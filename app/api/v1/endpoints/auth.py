"""
Endpoints de autenticación: login y verificación del token actual.

POST /api/v1/auth/login  → Recibe email + contraseña, devuelve JWT.
GET  /api/v1/auth/yo     → Retorna el usuario autenticado actual.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import obtener_servicio_usuario, obtener_usuario_actual
from app.core.config import obtener_configuracion
from app.core.limiter import limiter
from app.core.seguridad import crear_access_token
from app.esquemas.token import Token
from app.esquemas.usuario import RespuestaUsuario
from app.servicios.usuario import ServicioUsuario

router = APIRouter(prefix="/auth", tags=["Autenticación"])

_config = obtener_configuracion()


@router.post(
    "/login",
    response_model=Token,
    summary="Iniciar sesión",
    description=(
        "Autentica al usuario con email y contraseña. "
        "Devuelve un JWT de acceso con duración configurable. "
        "Incluye limitación de tasa (rate limiting) para prevenir ataques de fuerza bruta."
    ),
    responses={
        200: {"description": "Login exitoso, token JWT generado"},
        401: {"description": "Credenciales inválidas o cuenta inactiva"},
        429: {"description": "Demasiadas peticiones consecutivas (Rate Limit)"},
    },
)
@limiter.limit(_config.limite_auth)
async def login(
    request: Request,
    formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
    servicio: Annotated[ServicioUsuario, Depends(obtener_servicio_usuario)],
) -> Token:
    """
    Verifica credenciales y emite un token JWT de acceso.

    Usa OAuth2PasswordRequestForm para máxima compatibilidad con
    herramientas como Swagger UI (botón 'Authorize').
    El campo 'username' del formulario acepta el email del usuario.
    """
    usuario = await servicio.verificar_credenciales(
        email=formulario.username,
        contrasena=formulario.password,
    )
    token = crear_access_token(sub=str(usuario.id))
    return Token(
        access_token=token,
        token_type="bearer",
        expira_en=_config.jwt_expiracion_minutos * 60,
    )


@router.get(
    "/yo",
    response_model=RespuestaUsuario,
    summary="Obtener usuario autenticado",
    description="Retorna el perfil completo del usuario dueño del JWT enviado.",
    responses={
        200: {"description": "Datos del usuario autenticado"},
        401: {"description": "Token ausente, inválido o expirado"},
    },
)
async def obtener_yo(
    usuario_actual: Annotated[RespuestaUsuario, Depends(obtener_usuario_actual)],
) -> RespuestaUsuario:
    """Retorna el perfil del usuario autenticado."""
    return usuario_actual
