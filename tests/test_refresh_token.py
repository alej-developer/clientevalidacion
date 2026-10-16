"""
Tests de refresh tokens con rotación y revocación (PR 7).

Cubre: emisión en login (JSON + cookie httpOnly), rotación en /auth/refresh
(el token presentado queda revocado), rechazo de tokens inválidos,
revocados o expirados, y revocación en /auth/logout.
"""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seguridad import hashear_refresh_token
from app.modelos.refresh_token import RefreshToken

_USUARIO = {
    "nombre": "Usuario Refresh",
    "email": "refresh@ejemplo.com",
    "contrasena": "Password#123",
}


async def _registrar_y_loguear(cliente: AsyncClient) -> dict:
    await cliente.post("/api/v1/usuarios", json=_USUARIO)
    respuesta = await cliente.post(
        "/api/v1/auth/login",
        data={"username": _USUARIO["email"], "password": _USUARIO["contrasena"]},
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


async def test_login_devuelve_refresh_token_y_cookie(cliente_async: AsyncClient) -> None:
    """El login devuelve refresh_token en JSON y fija su cookie httpOnly."""
    respuesta_login = await cliente_async.post(
        "/api/v1/auth/login",
        data={"username": _USUARIO["email"], "password": _USUARIO["contrasena"]},
    )
    assert respuesta_login.status_code == 401  # aún no registrado

    await cliente_async.post("/api/v1/usuarios", json=_USUARIO)
    tokens = await _registrar_y_loguear(cliente_async)
    assert tokens["refresh_token"]

    # Cookie httpOnly de refresh, restringida a /api/v1/auth
    cookies = cliente_async.cookies
    assert "cv_refresh_token" in cookies


async def test_refresh_rota_y_el_anterior_queda_revocado(
    cliente_async: AsyncClient,
) -> None:
    """POST /auth/refresh emite un par nuevo; reutilizar el viejo da 401."""
    tokens = await _registrar_y_loguear(cliente_async)

    # Con cookie (flujo frontend): requiere la cabecera CSRF
    respuesta = await cliente_async.post(
        "/api/v1/auth/refresh",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert respuesta.status_code == 200, respuesta.text
    nuevos = respuesta.json()
    assert nuevos["access_token"]
    assert nuevos["refresh_token"] != tokens["refresh_token"]

    # Reutilización del refresh token rotado → 401
    cliente_async.cookies.clear()
    reutilizacion = await cliente_async.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert reutilizacion.status_code == 401


async def test_refresh_con_cuerpo_json_sin_cookies(cliente_async: AsyncClient) -> None:
    """El refresh también funciona con el token en el cuerpo (clientes API)."""
    tokens = await _registrar_y_loguear(cliente_async)
    cliente_async.cookies.clear()
    respuesta = await cliente_async.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["access_token"]


async def test_refresh_con_token_invalido_devuelve_401(cliente_async: AsyncClient) -> None:
    """Un refresh token desconocido se rechaza con 401."""
    await _registrar_y_loguear(cliente_async)
    cliente_async.cookies.clear()  # flujo cliente API (sin cookies, sin CSRF)
    respuesta = await cliente_async.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "token-que-no-existe"},
    )
    assert respuesta.status_code == 401


async def test_refresh_sin_token_devuelve_401(cliente_async: AsyncClient) -> None:
    """Sin cuerpo ni cookie, /auth/refresh devuelve 401."""
    respuesta = await cliente_async.post("/api/v1/auth/refresh")
    assert respuesta.status_code == 401


async def test_logout_revoca_el_refresh_token(cliente_async: AsyncClient) -> None:
    """Tras logout, el refresh token queda revocado y no puede rotar."""
    tokens = await _registrar_y_loguear(cliente_async)
    respuesta = await cliente_async.post(
        "/api/v1/auth/logout",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert respuesta.status_code == 204

    cliente_async.cookies.clear()
    reintento = await cliente_async.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert reintento.status_code == 401


async def test_refresh_expirado_devuelve_401(
    cliente_async: AsyncClient, sesion_db: AsyncSession
) -> None:
    """Un refresh token cuya expiración ya pasó se rechaza con 401."""
    tokens = await _registrar_y_loguear(cliente_async)

    # Forzar la expiración del token directamente en BD
    from sqlalchemy import select

    resultado = await sesion_db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == hashear_refresh_token(tokens["refresh_token"])
        )
    )
    fila = resultado.scalar_one()
    fila.expira_en = datetime.now(tz=UTC) - timedelta(minutes=1)
    await sesion_db.commit()

    cliente_async.cookies.clear()
    respuesta = await cliente_async.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert respuesta.status_code == 401


async def test_access_token_renovado_es_valido(cliente_async: AsyncClient) -> None:
    """El access token emitido por /auth/refresh autentica en /auth/yo."""
    await _registrar_y_loguear(cliente_async)
    respuesta = await cliente_async.post(
        "/api/v1/auth/refresh",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert respuesta.status_code == 200
    nuevo_access = respuesta.json()["access_token"]
    yo = await cliente_async.get(
        "/api/v1/auth/yo",
        headers={"Authorization": f"Bearer {nuevo_access}"},
    )
    assert yo.status_code == 200
    assert yo.json()["email"] == _USUARIO["email"]
