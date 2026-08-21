"""
Utilidades de seguridad: generación y verificación de tokens JWT.

Usa python-jose para crear access tokens firmados con HS256.
La verificación de contraseñas reutiliza el PBKDF2 ya implementado
en ServicioUsuario para mantener consistencia en el proyecto.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.core.config import obtener_configuracion
from app.core.logging import obtener_logger

_logger = obtener_logger("core.seguridad")
_config = obtener_configuracion()

# Algoritmo de firma
ALGORITMO = "HS256"


def crear_access_token(
    sub: str,
    datos_extra: dict[str, Any] | None = None,
) -> str:
    """
    Genera un JWT de acceso firmado con la clave secreta de la aplicación.

    Args:
        sub: Identificador del sujeto (normalmente el UUID del usuario).
        datos_extra: Campos adicionales a incluir en el payload.

    Retorna:
        Token JWT firmado como cadena de texto.
    """
    ahora = datetime.now(tz=UTC)
    expira = ahora + timedelta(minutes=_config.jwt_expiracion_minutos)

    payload: dict[str, Any] = {
        "sub": sub,
        "iat": ahora,
        "exp": expira,
        "tipo": "access",
    }
    if datos_extra:
        payload.update(datos_extra)

    token = jwt.encode(payload, _config.jwt_secreto, algorithm=ALGORITMO)
    _logger.debug("Token JWT generado para sub='%s', exp='%s'", sub, expira)
    return token


def decodificar_token(token: str) -> dict[str, Any]:
    """
    Decodifica y valida un JWT.

    Args:
        token: Token JWT a validar.

    Retorna:
        Payload decodificado como diccionario.

    Raises:
        JWTError: Si el token es inválido, ha expirado o la firma no coincide.
    """
    return jwt.decode(token, _config.jwt_secreto, algorithms=[ALGORITMO])  # type: ignore[no-any-return]


def extraer_sub(token: str) -> str | None:
    """
    Extrae el campo 'sub' (subject) de un JWT sin lanzar excepción.

    Útil para logs o debugging donde no se necesita propagar el error.

    Args:
        token: Token JWT a inspeccionar.

    Retorna:
        El valor de 'sub' o None si el token es inválido.
    """
    try:
        payload = decodificar_token(token)
        return str(payload.get("sub"))
    except JWTError:
        return None
