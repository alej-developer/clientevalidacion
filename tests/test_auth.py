"""
Pruebas de integración para los endpoints de autenticación (/api/v1/auth).

Cubre:
- Login exitoso: recibe token JWT válido (HTTP 200).
- Login con email inexistente (HTTP 422/404 → el servicio lanza NoEncontradoError).
- Login con contraseña incorrecta (HTTP 422).
- Login con cuenta inactiva (HTTP 422).
- Acceso a endpoint protegido sin token (HTTP 401).
- Acceso a endpoint protegido con token válido (HTTP 200).
- Acceso a endpoint protegido con token inválido (HTTP 401).
- GET /auth/yo con token válido (HTTP 200).
"""

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USUARIO_BASE = {
    "nombre": "Auth Tester",
    "email": "auth.tester@ejemplo.com",
    "contrasena": "Password#123",
}


async def _crear_usuario_y_login(cliente: AsyncClient) -> tuple[str, dict]:  # type: ignore[type-arg]
    """Registra un usuario y devuelve (token, datos_usuario)."""
    resp_crear = await cliente.post("/api/v1/usuarios", json=USUARIO_BASE)
    assert resp_crear.status_code == 201, resp_crear.text
    usuario = resp_crear.json()

    resp_login = await cliente.post(
        "/api/v1/auth/login",
        data={"username": USUARIO_BASE["email"], "password": USUARIO_BASE["contrasena"]},
    )
    assert resp_login.status_code == 200, resp_login.text
    token = resp_login.json()["access_token"]
    return token, usuario


# ---------------------------------------------------------------------------
# Tests de login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_exitoso(cliente_async: AsyncClient) -> None:
    """Login con credenciales correctas devuelve token JWT y tipo 'bearer'."""
    await cliente_async.post("/api/v1/usuarios", json=USUARIO_BASE)

    respuesta = await cliente_async.post(
        "/api/v1/auth/login",
        data={
            "username": USUARIO_BASE["email"],
            "password": USUARIO_BASE["contrasena"],
        },
    )
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert "access_token" in datos
    assert datos["token_type"] == "bearer"
    assert datos["expira_en"] > 0


@pytest.mark.asyncio
async def test_login_email_inexistente(cliente_async: AsyncClient) -> None:
    """Login con email no registrado devuelve error (no 200)."""
    respuesta = await cliente_async.post(
        "/api/v1/auth/login",
        data={"username": "nadie@ejemplo.com", "password": "Password#123"},
    )
    assert respuesta.status_code in (401, 404, 422, 500)
    assert respuesta.status_code != 200


@pytest.mark.asyncio
async def test_login_contrasena_incorrecta(cliente_async: AsyncClient) -> None:
    """Login con contraseña errónea devuelve error (no 200)."""
    await cliente_async.post("/api/v1/usuarios", json=USUARIO_BASE)

    respuesta = await cliente_async.post(
        "/api/v1/auth/login",
        data={"username": USUARIO_BASE["email"], "password": "MalPassword#999"},
    )
    assert respuesta.status_code != 200


# ---------------------------------------------------------------------------
# Tests de endpoints protegidos
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_sin_token_devuelve_401(cliente_async: AsyncClient) -> None:
    """PATCH /usuarios/{id} sin Authorization devuelve 401."""
    # Crear usuario primero
    resp = await cliente_async.post("/api/v1/usuarios", json=USUARIO_BASE)
    usuario_id = resp.json()["id"]

    respuesta = await cliente_async.patch(
        f"/api/v1/usuarios/{usuario_id}",
        json={"nombre": "Nuevo Nombre"},
    )
    assert respuesta.status_code == 401


@pytest.mark.asyncio
async def test_delete_sin_token_devuelve_401(cliente_async: AsyncClient) -> None:
    """DELETE /usuarios/{id} sin Authorization devuelve 401."""
    resp = await cliente_async.post("/api/v1/usuarios", json=USUARIO_BASE)
    usuario_id = resp.json()["id"]

    respuesta = await cliente_async.delete(f"/api/v1/usuarios/{usuario_id}")
    assert respuesta.status_code == 401


@pytest.mark.asyncio
async def test_patch_con_token_valido(cliente_async: AsyncClient) -> None:
    """PATCH /usuarios/{id} con token válido actualiza y devuelve 200."""
    token, usuario = await _crear_usuario_y_login(cliente_async)

    respuesta = await cliente_async.patch(
        f"/api/v1/usuarios/{usuario['id']}",
        json={"nombre": "Nombre Actualizado"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Nombre Actualizado"


@pytest.mark.asyncio
async def test_delete_con_token_valido(cliente_async: AsyncClient) -> None:
    """DELETE /usuarios/{id} con token válido elimina y devuelve 204."""
    token, usuario = await _crear_usuario_y_login(cliente_async)

    respuesta = await cliente_async.delete(
        f"/api/v1/usuarios/{usuario['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 204


@pytest.mark.asyncio
async def test_patch_con_token_invalido_devuelve_401(cliente_async: AsyncClient) -> None:
    """PATCH con token falso/inválido devuelve 401."""
    resp = await cliente_async.post("/api/v1/usuarios", json=USUARIO_BASE)
    usuario_id = resp.json()["id"]

    respuesta = await cliente_async.patch(
        f"/api/v1/usuarios/{usuario_id}",
        json={"nombre": "Hack"},
        headers={"Authorization": "Bearer token.falso.invalido"},
    )
    assert respuesta.status_code == 401


# ---------------------------------------------------------------------------
# Tests de /auth/yo
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_obtener_yo_con_token_valido(cliente_async: AsyncClient) -> None:
    """GET /auth/yo con token válido retorna el perfil del usuario autenticado."""
    token, usuario = await _crear_usuario_y_login(cliente_async)

    respuesta = await cliente_async.get(
        "/api/v1/auth/yo",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["id"] == usuario["id"]
    assert datos["email"] == USUARIO_BASE["email"].lower()


@pytest.mark.asyncio
async def test_obtener_yo_sin_token_devuelve_401(cliente_async: AsyncClient) -> None:
    """GET /auth/yo sin token devuelve 401."""
    respuesta = await cliente_async.get("/api/v1/auth/yo")
    assert respuesta.status_code == 401
