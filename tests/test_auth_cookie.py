"""
Tests de autenticación por cookie httpOnly y protección CSRF (PR 6).

Cubre: login que fija la cookie httpOnly (Bearer sigue funcionando),
acceso con cookie a endpoints protegidos, logout que la borra, y la
cabecera X-Requested-With exigida en mutaciones autenticadas por cookie.
"""

from httpx import AsyncClient

from app.core.config import Configuracion, _cookie_segura_efectiva

_USUARIO = {
    "nombre": "Usuario Cookie",
    "email": "cookie@ejemplo.com",
    "contrasena": "Password#123",
}


async def _registrar(cliente: AsyncClient) -> str:
    respuesta = await cliente.post("/api/v1/usuarios", json=_USUARIO)
    assert respuesta.status_code == 201, respuesta.text
    return str(respuesta.json()["id"])


async def _login(cliente: AsyncClient) -> None:
    respuesta = await cliente.post(
        "/api/v1/auth/login",
        data={"username": _USUARIO["email"], "password": _USUARIO["contrasena"]},
    )
    assert respuesta.status_code == 200, respuesta.text


async def test_login_setea_cookie_httponly_y_sigue_devolviendo_token(
    cliente_async: AsyncClient,
) -> None:
    """El login ficia la cookie httpOnly y mantiene el token JSON (Bearer)."""
    await _registrar(cliente_async)
    respuesta = await cliente_async.post(
        "/api/v1/auth/login",
        data={"username": _USUARIO["email"], "password": _USUARIO["contrasena"]},
    )
    assert respuesta.status_code == 200
    set_cookie = respuesta.headers["set-cookie"]
    assert "cv_access_token=" in set_cookie
    assert "httponly" in set_cookie.lower()
    assert "access_token" in respuesta.json()


async def test_yo_con_cookie_sin_cabecera(cliente_async: AsyncClient) -> None:
    """GET /auth/yo funciona con la cookie httpOnly, sin Bearer."""
    await _registrar(cliente_async)
    await _login(cliente_async)
    respuesta = await cliente_async.get("/api/v1/auth/yo")
    assert respuesta.status_code == 200
    assert respuesta.json()["email"] == _USUARIO["email"]


async def test_logout_borra_la_cookie(cliente_async: AsyncClient) -> None:
    """POST /auth/logout elimina la cookie: el acceso posterior es 401."""
    await _registrar(cliente_async)
    await _login(cliente_async)
    assert (await cliente_async.get("/api/v1/auth/yo")).status_code == 200

    respuesta = await cliente_async.post("/api/v1/auth/logout")
    assert respuesta.status_code == 204
    assert "cv_access_token" in respuesta.headers["set-cookie"]

    assert (await cliente_async.get("/api/v1/auth/yo")).status_code == 401


async def test_mutacion_con_cookie_sin_cabecera_csrf_devuelve_403(
    cliente_async: AsyncClient,
) -> None:
    """PATCH autenticado por cookie sin X-Requested-With es rechazado (CSRF)."""
    usuario_id = await _registrar(cliente_async)
    await _login(cliente_async)
    respuesta = await cliente_async.patch(
        f"/api/v1/usuarios/{usuario_id}",
        json={"nombre": "Nombre Nuevo Cookie"},
    )
    assert respuesta.status_code == 403
    assert "x-requested-with" in respuesta.json()["error"]


async def test_mutacion_con_cookie_y_cabecera_csrf_funciona(
    cliente_async: AsyncClient,
) -> None:
    """PATCH autenticado por cookie con X-Requested-With funciona."""
    usuario_id = await _registrar(cliente_async)
    await _login(cliente_async)
    respuesta = await cliente_async.patch(
        f"/api/v1/usuarios/{usuario_id}",
        json={"nombre": "Nombre Nuevo Cookie"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Nombre Nuevo Cookie"


async def test_mutacion_con_bearer_no_exige_cabecera_csrf(
    cliente_async: AsyncClient,
) -> None:
    """PATCH con Bearer (sin cookie) no necesita X-Requested-With."""
    usuario_id = await _registrar(cliente_async)
    resp_login = await cliente_async.post(
        "/api/v1/auth/login",
        data={"username": _USUARIO["email"], "password": _USUARIO["contrasena"]},
    )
    token = resp_login.json()["access_token"]
    respuesta = await cliente_async.patch(
        f"/api/v1/usuarios/{usuario_id}",
        json={"nombre": "Nombre Bearer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 200


def test_cookie_segura_se_resuelve_por_entorno(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Secure por defecto fuera de debug; explícita si COOKIE_SEGURA se define."""
    # El conftest fija COOKIE_SEGURA=false; lo aislamos para probar la lógica.
    monkeypatch.delenv("COOKIE_SEGURA", raising=False)
    assert _cookie_segura_efectiva(Configuracion(app_debug=False)) is True
    assert _cookie_segura_efectiva(Configuracion(app_debug=True)) is False
    assert _cookie_segura_efectiva(Configuracion(app_debug=False, cookie_segura=False)) is False
    assert _cookie_segura_efectiva(Configuracion(app_debug=True, cookie_segura=True)) is True
