"""
Tests de hardening de configuración y logging (PR 5 del plan).

Cubre: rechazo del JWT_SECRETO por defecto en producción, cabeceras
X-RateLimit visibles, ausencia de PII (emails) en los logs y la
validación de contraseña compartida entre esquemas.
"""

import logging

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.core.config import JWT_SECRETO_POR_DEFECTO, Configuracion
from app.esquemas.usuario import ActualizarUsuario, CrearUsuario


def test_config_rechaza_secreto_por_defecto_en_produccion() -> None:
    """APP_DEBUG=false + JWT_SECRETO por defecto: la configuración falla."""
    with pytest.raises(ValidationError, match="JWT_SECRETO"):
        Configuracion(app_debug=False, jwt_secreto=JWT_SECRETO_POR_DEFECTO)


def test_config_acepta_secreto_fuerte_en_produccion() -> None:
    """APP_DEBUG=false + secreto propio: la configuración es válida."""
    config = Configuracion(app_debug=False, jwt_secreto="secreto-fuerte-de-produccion-1234567890")
    assert config.jwt_secreto.startswith("secreto-fuerte")


def test_config_permite_secreto_por_defecto_en_debug() -> None:
    """APP_DEBUG=true permite el secreto por defecto (desarrollo local)."""
    config = Configuracion(app_debug=True, jwt_secreto=JWT_SECRETO_POR_DEFECTO)
    assert config.app_debug is True


async def test_login_expone_cabeceras_rate_limit(cliente_async: AsyncClient) -> None:
    """Las respuestas de rutas limitadas incluyen cabeceras X-RateLimit-*."""
    await cliente_async.post(
        "/api/v1/usuarios",
        json={
            "nombre": "Usuario Rate",
            "email": "rate@ejemplo.com",
            "contrasena": "Password#123",
        },
    )
    respuesta = await cliente_async.post(
        "/api/v1/auth/login",
        data={"username": "rate@ejemplo.com", "password": "Password#123"},
    )
    assert respuesta.status_code == 200
    assert "x-ratelimit-limit" in respuesta.headers
    assert "x-ratelimit-remaining" in respuesta.headers


async def test_logs_no_contienen_email(
    cliente_async: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Los logs del flujo de registro y login no contienen el email (PII)."""
    with caplog.at_level(logging.INFO, logger="app"):
        await cliente_async.post(
            "/api/v1/usuarios",
            json={
                "nombre": "Usuario Logs",
                "email": "privado@ejemplo.com",
                "contrasena": "Password#123",
            },
        )
        await cliente_async.post(
            "/api/v1/auth/login",
            data={"username": "privado@ejemplo.com", "password": "Password#123"},
        )
    assert "privado@ejemplo.com" not in caplog.text


def test_validacion_contrasena_compartida() -> None:
    """CrearUsuario y ActualizarUsuario aplican exactamente las mismas reglas."""
    datos_base = {"nombre": "Usuario Valido", "email": "valido@ejemplo.com"}
    for contrasena_mala in ("sinmayuscula#1", "SINMINUSCULA#1", "SinDigitos#", "SinEspecial1a"):
        with pytest.raises(ValidationError):
            CrearUsuario(**datos_base, contrasena=contrasena_mala)
        with pytest.raises(ValidationError):
            ActualizarUsuario(contrasena=contrasena_mala)
