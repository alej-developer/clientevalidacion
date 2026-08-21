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
async def test_restaurar_usuario_eliminado(cliente_async: AsyncClient) -> None:
    """POST /restaurar recupera al usuario eliminado, que vuelve a ser visible."""
    token, usuario = await _crear_y_login(cliente_async, USUARIO_BASE)
    usuario_id = usuario["id"]

    # Soft delete
    await cliente_async.delete(
        f"/api/v1/usuarios/{usuario_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    # Confirmar que está oculto
    assert (await cliente_async.get(f"/api/v1/usuarios/{usuario_id}")).status_code == 404

    # Necesitamos un token válido para restaurar — crear admin o reutilizar otro
    # En este caso creamos un segundo usuario y usamos su token
    admin_payload = {
        "nombre": "Admin Restaurador",
        "email": "admin@ejemplo.com",
        "contrasena": "Password#123",
    }
    admin_token, _ = await _crear_y_login(cliente_async, admin_payload)

    # Restaurar
    resp_restaurar = await cliente_async.post(
        f"/api/v1/usuarios/{usuario_id}/restaurar",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_restaurar.status_code == 200
    datos = resp_restaurar.json()
    assert datos["id"] == usuario_id
    assert datos["eliminado_en"] is None

    # Ahora vuelve a ser visible
    resp_get = await cliente_async.get(f"/api/v1/usuarios/{usuario_id}")
    assert resp_get.status_code == 200


@pytest.mark.asyncio
async def test_restaurar_id_inexistente_devuelve_404(cliente_async: AsyncClient) -> None:
    """Restaurar un UUID que no corresponde a ningún usuario eliminado devuelve 404."""
    import uuid

    token, _ = await _crear_y_login(cliente_async, USUARIO_BASE)
    uuid_falso = str(uuid.uuid4())

    resp = await cliente_async.post(
        f"/api/v1/usuarios/{uuid_falso}/restaurar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


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
