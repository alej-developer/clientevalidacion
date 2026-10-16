"""
Inyección de dependencias para los endpoints de la API.

Proporciona funciones generadoras de dependencias para instanciar
servicios de negocio inyectando la sesión de base de datos asíncrona,
y la dependencia de autenticación JWT para proteger endpoints.
"""

import uuid
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import obtener_configuracion
from app.core.database import obtener_db
from app.core.excepciones.excepciones import NoAutorizadoError
from app.core.seguridad import NOMBRE_COOKIE_AUTH, decodificar_token
from app.esquemas.usuario import RespuestaUsuario
from app.servicios.autenticacion import ServicioAutenticacion
from app.servicios.usuario import ServicioUsuario

# Esquema OAuth2 — apunta al endpoint de login para Swagger UI.
# auto_error=False: la autenticación también puede venir por cookie httpOnly;
# si no hay ni Bearer ni cookie, se devuelve 401 manualmente.
_oauth2_esquema = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
_config = obtener_configuracion()


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


def obtener_servicio_autenticacion(
    sesion: Annotated[AsyncSession, Depends(obtener_db)],
) -> ServicioAutenticacion:
    """Inyecta una instancia de ServicioAutenticacion con la sesión actual."""
    return ServicioAutenticacion(sesion=sesion)


async def obtener_usuario_actual(
    request: Request,
    token_bearer: Annotated[str | None, Depends(_oauth2_esquema)],
    servicio: Annotated[ServicioUsuario, Depends(obtener_servicio_usuario)],
) -> RespuestaUsuario:
    """
    Dependencia de autenticación JWT dual: Bearer o cookie httpOnly.

    Acepta el token en la cabecera Authorization (Swagger, curl, scripts)
    o en la cookie httpOnly que fija POST /auth/login (frontend web).
    Extrae el UUID del usuario y lo recupera de la base de datos.

    Args:
        request: Petición HTTP (para leer la cookie si no hay Bearer).
        token_bearer: JWT de la cabecera Authorization, si viene.
        servicio: Servicio de usuarios para consultar la base de datos.

    Retorna:
        RespuestaUsuario del usuario autenticado.

    Raises:
        NoAutorizadoError: Si no hay credenciales, son inválidas o el usuario no existe.
    """
    token = token_bearer or request.cookies.get(NOMBRE_COOKIE_AUTH)
    if token is None:
        raise NoAutorizadoError(
            mensaje="Autenticación requerida: cabecera Bearer o cookie de sesión."
        )
    try:
        payload = decodificar_token(token)
        sub: str | None = payload.get("sub")
        if sub is None:
            raise NoAutorizadoError(mensaje="Token inválido: 'sub' ausente.")
        usuario_id = uuid.UUID(sub)
    except (JWTError, ValueError) as exc:
        raise NoAutorizadoError(mensaje="Token inválido o expirado.") from exc

    try:
        return await servicio.obtener_usuario(usuario_id)
    except Exception as exc:
        raise NoAutorizadoError(mensaje="Usuario del token no encontrado.") from exc
