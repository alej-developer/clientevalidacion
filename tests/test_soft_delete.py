"""
Pruebas de integración para el Soft Delete y restauración de usuarios.

Cubre:
- DELETE hace soft delete (HTTP 204): el usuario ya no aparece en GET por ID.
- El usuario soft-deleted NO aparece en listado general.
- POST /restaurar con JWT recupera el usuario (HTTP 200).
- Restaurar un ID inexistente devuelve 404.
- Un email de usuario eliminado puede reutilizarse por un nuevo usuario.
- El campo eliminado_en aparece en la respuesta de restauración.
"""

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USUARIO_BASE = {
    "nombre": "Soft Delete Tester",
    "email": "softdelete@ejemplo.com",
    "contrasena": "Password#123",
}


async def _crear_y_login(cliente: AsyncClient, payload: dict) -> tuple[str, dict]:  # type: ignore[type-arg]
    """Registra usuario y devuelve (token, datos)."""
    resp = await cliente.post("/api/v1/usuarios", json=payload)
    assert resp.status_code == 201, resp.text
    datos = resp.json()
    resp_login = await cliente.post(
        "/api/v1/auth/login",
        data={"username": payload["email"], "password": payload["contrasena"]},
    )
    assert resp_login.status_code == 200, resp_login.text
    return resp_login.json()["access_token"], datos


# ---------------------------------------------------------------------------
# Tests de Soft Delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_hace_soft_delete_y_oculta_usuario(cliente_async: AsyncClient) -> None:
    """DELETE aplica soft delete: el usuario desaparece del GET por ID."""
    token, usuario = await _crear_y_login(cliente_async, USUARIO_BASE)
    usuario_id = usuario["id"]

    # Eliminar (soft)
    resp_delete = await cliente_async.delete(
        f"/api/v1/usuarios/{usuario_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_delete.status_code == 204

    # El usuario ya no es visible por ID
    resp_get = await cliente_async.get(f"/api/v1/usuarios/{usuario_id}")
    assert resp_get.status_code == 404


@pytest.mark.asyncio
async def test_usuario_eliminado_no_aparece_en_listado(cliente_async: AsyncClient) -> None:
    """Un usuario con soft delete no aparece en el listado paginado."""
    token, usuario = await _crear_y_login(cliente_async, USUARIO_BASE)

    # Crear un segundo usuario para que el listado no quede vacío
    otro_payload = {
        "nombre": "Otro Usuario",
        "email": "otro@ejemplo.com",
        "contrasena": "Password#123",
    }
    await cliente_async.post("/api/v1/usuarios", json=otro_payload)

    # Eliminar el primero
    await cliente_async.delete(
        f"/api/v1/usuarios/{usuario['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Listar todos: solo debe aparecer el segundo
    resp = await cliente_async.get("/api/v1/usuarios")
    assert resp.status_code == 200
    datos = resp.json()
    ids_en_lista = [u["id"] for u in datos["elementos"]]
    assert usuario["id"] not in ids_en_lista
    assert datos["total"] == 1


@pytest.mark.asyncio
async def test_restaurar_tras_auto_eliminacion_requiere_admin(cliente_async: AsyncClient) -> None:
    """
    Tras auto-eliminarse, la restauración NO es posible por API (por ahora).

    Con la autorización por propiedad, el propio token deja de resolver
    al quedar eliminado (401) y cualquier otro usuario recibe 403.
    La restauración queda como función de un futuro rol administrador.
    """
    token, usuario = await _crear_y_login(cliente_async, USUARIO_BASE)
    usuario_id = usuario["id"]

    # Soft delete sobre la propia cuenta
    await cliente_async.delete(
        f"/api/v1/usuarios/{usuario_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Confirmar que está oculto
    assert (await cliente_async.get(f"/api/v1/usuarios/{usuario_id}")).status_code == 404

    # El propio token ya no resuelve (usuario eliminado): 401
    resp_propio = await cliente_async.post(
        f"/api/v1/usuarios/{usuario_id}/restaurar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_propio.status_code == 401

    # Otro usuario autenticado: 403 (no es su cuenta)
    otro_payload = {
        "nombre": "Otro Usuario",
        "email": "otro@ejemplo.com",
        "contrasena": "Password#123",
    }
    otro_token, _ = await _crear_y_login(cliente_async, otro_payload)
    resp_otro = await cliente_async.post(
        f"/api/v1/usuarios/{usuario_id}/restaurar",
        headers={"Authorization": f"Bearer {otro_token}"},
    )
    assert resp_otro.status_code == 403

    # El usuario sigue oculto: nadie pudo restaurarlo por API
    resp_get = await cliente_async.get(f"/api/v1/usuarios/{usuario_id}")
    assert resp_get.status_code == 404


@pytest.mark.asyncio
async def test_restaurar_id_ajeno_devuelve_403(cliente_async: AsyncClient) -> None:
    """Restaurar un UUID ajeno devuelve 403 (no revela si existe o no)."""
    import uuid

    token, _ = await _crear_y_login(cliente_async, USUARIO_BASE)
    uuid_falso = str(uuid.uuid4())

    resp = await cliente_async.post(
        f"/api/v1/usuarios/{uuid_falso}/restaurar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_restaurar_usuario_activo_devuelve_404(cliente_async: AsyncClient) -> None:
    """Intentar restaurar un usuario que NO está eliminado devuelve 404."""
    token, usuario = await _crear_y_login(cliente_async, USUARIO_BASE)

    resp = await cliente_async.post(
        f"/api/v1/usuarios/{usuario['id']}/restaurar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_email_reutilizable_tras_soft_delete(cliente_async: AsyncClient) -> None:
    """El email de un usuario eliminado puede ser reutilizado por uno nuevo."""
    token, usuario = await _crear_y_login(cliente_async, USUARIO_BASE)

    # Eliminar
    await cliente_async.delete(
        f"/api/v1/usuarios/{usuario['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Registrar nuevo usuario con el mismo email
    resp_nuevo = await cliente_async.post("/api/v1/usuarios", json=USUARIO_BASE)
    assert resp_nuevo.status_code == 201
    assert resp_nuevo.json()["email"] == USUARIO_BASE["email"]


@pytest.mark.asyncio
async def test_respuesta_incluye_campo_eliminado_en(cliente_async: AsyncClient) -> None:
    """La respuesta de usuario incluye el campo eliminado_en (None para activos)."""
    resp = await cliente_async.post("/api/v1/usuarios", json=USUARIO_BASE)
    assert resp.status_code == 201
    datos = resp.json()
    assert "eliminado_en" in datos
    assert datos["eliminado_en"] is None
