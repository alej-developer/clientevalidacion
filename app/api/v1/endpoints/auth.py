"""
Endpoints de autenticación: login y verificación del token actual.

POST /api/v1/auth/login  → Recibe email + contraseña, devuelve JWT.
GET  /api/v1/auth/yo     → Retorna el usuario autenticado actual.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import (
    obtener_servicio_autenticacion,
    obtener_servicio_usuario,
    obtener_usuario_actual,
)
from app.core.config import _cookie_segura_efectiva, obtener_configuracion
from app.core.excepciones.excepciones import NoAutorizadoError
from app.core.limiter import limiter
from app.core.seguridad import (
    NOMBRE_COOKIE_AUTH,
    NOMBRE_COOKIE_REFRESH,
    RUTA_COOKIE_REFRESH,
    crear_access_token,
)
from app.esquemas.token import PeticionRefresh, Token
from app.esquemas.usuario import RespuestaUsuario
from app.servicios.autenticacion import ServicioAutenticacion
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
        401: {"description": "Credenciales inválidas (respuesta genérica anti-enumeración)"},
        429: {"description": "Demasiadas peticiones consecutivas (Rate Limit)"},
    },
)
@limiter.limit(_config.limite_auth)
async def login(
    request: Request,
    response: Response,
    formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
    servicio: Annotated[ServicioUsuario, Depends(obtener_servicio_usuario)],
    servicio_auth: Annotated[ServicioAutenticacion, Depends(obtener_servicio_autenticacion)],
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
    refresh = await servicio_auth.emitir_refresh(usuario.id)
    expira_en = _config.jwt_expiracion_minutos * 60
    _fijar_cookies_sesion(response, token, refresh, expira_en)
    return Token(
        access_token=token,
        refresh_token=refresh,
        token_type="bearer",
        expira_en=expira_en,
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


def _fijar_cookies_sesion(response: Response, token: str, refresh: str, expira_en: int) -> None:
    """Fija las cookies httpOnly de acceso y refresh tras login o refresh."""
    segura = _cookie_segura_efectiva(_config)
    response.set_cookie(
        key=NOMBRE_COOKIE_AUTH,
        value=token,
        max_age=expira_en,
        httponly=True,
        secure=segura,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=NOMBRE_COOKIE_REFRESH,
        value=refresh,
        max_age=_config.jwt_refresh_expiracion_dias * 86400,
        httponly=True,
        secure=segura,
        samesite="lax",
        path=RUTA_COOKIE_REFRESH,  # solo viaja a /api/v1/auth/*
    )


def _borrar_cookies_sesion(response: Response) -> None:
    """Elimina las cookies httpOnly de acceso y refresh."""
    segura = _cookie_segura_efectiva(_config)
    response.delete_cookie(
        key=NOMBRE_COOKIE_AUTH, httponly=True, secure=segura, samesite="lax", path="/"
    )
    response.delete_cookie(
        key=NOMBRE_COOKIE_REFRESH,
        httponly=True,
        secure=segura,
        samesite="lax",
        path=RUTA_COOKIE_REFRESH,
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Renovar tokens",
    description=(
        "Rota el refresh token (cuerpo JSON o cookie httpOnly) y devuelve "
        "un nuevo par access + refresh. El refresh presentado queda revocado: "
        "reutilizarlo devuelve 401."
    ),
    responses={
        200: {"description": "Tokens renovados"},
        401: {"description": "Refresh token inválido, revocado o expirado"},
        429: {"description": "Demasiadas peticiones consecutivas (Rate Limit)"},
    },
)
@limiter.limit(_config.limite_auth)
async def refresh(
    request: Request,
    response: Response,
    servicio_auth: Annotated[ServicioAutenticacion, Depends(obtener_servicio_autenticacion)],
    cuerpo: PeticionRefresh | None = None,
) -> Token:
    """Rota el refresh token y emite un nuevo par de tokens."""
    token_refresh = (cuerpo.refresh_token if cuerpo else None) or request.cookies.get(
        NOMBRE_COOKIE_REFRESH
    )
    if token_refresh is None:
        raise NoAutorizadoError(mensaje="Falta el refresh token (cuerpo o cookie httpOnly).")
    usuario_id, nuevo_refresh = await servicio_auth.rotar_refresh(token_refresh)
    token = crear_access_token(sub=str(usuario_id))
    expira_en = _config.jwt_expiracion_minutos * 60
    _fijar_cookies_sesion(response, token, nuevo_refresh, expira_en)
    return Token(
        access_token=token,
        refresh_token=nuevo_refresh,
        token_type="bearer",
        expira_en=expira_en,
    )


@router.post(
    "/logout",
    status_code=204,
    summary="Cerrar sesión",
    description=(
        "Revoca el refresh token (si viene en cookie o cuerpo) y borra las "
        "cookies httpOnly de sesión. No requiere autenticación. El access "
        "token Bearer sigue válido hasta su expiración natural (corta)."
    ),
    responses={
        204: {"description": "Sesión cerrada (refresh revocado, cookies eliminadas)"},
    },
)
async def logout(
    request: Request,
    response: Response,
    servicio_auth: Annotated[ServicioAutenticacion, Depends(obtener_servicio_autenticacion)],
    cuerpo: PeticionRefresh | None = None,
) -> None:
    """Revoca el refresh token y elimina las cookies de sesión."""
    token_refresh = (cuerpo.refresh_token if cuerpo else None) or request.cookies.get(
        NOMBRE_COOKIE_REFRESH
    )
    if token_refresh is not None:
        await servicio_auth.revocar_refresh(token_refresh)
    _borrar_cookies_sesion(response)
