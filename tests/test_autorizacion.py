"""
Tests de autorización por propiedad (PR: cada usuario solo gestiona su cuenta).

Verifica que un usuario autenticado NO puede modificar, borrar ni
restaurar la cuenta de otro (HTTP 403), y que sí puede operar sobre
la suya propia.
"""

import uuid

from httpx import AsyncClient

_USUARIO_A = {
    "nombre": "Usuario Uno",
    "email": "usuario.uno@ejemplo.com",
    "contrasena": "Password#123",
}
_USUARIO_B = {
    "nombre": "Usuario Dos",
    "email": "usuario.dos@ejemplo.com",
    "contrasena": "Password#456",
}


async def _registrar(cliente: AsyncClient, datos: dict) -> str:
    """Registra un usuario y devuelve su UUID."""
    respuesta = await cliente.post("/api/v1/usuarios", json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return str(respuesta.json()["id"])


async def _token(cliente: AsyncClient, datos: dict) -> dict[str, str]:
    """Hace login y devuelve la cabecera Authorization."""
    respuesta = await cliente.post(
        "/api/v1/auth/login",
        data={"username": datos["email"], "password": datos["contrasena"]},
    )
    assert respuesta.status_code == 200, respuesta.text
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


async def test_otro_usuario_no_puede_modificar(cliente_async: AsyncClient) -> None:
    """PATCH sobre la cuenta de otro usuario devuelve 403."""
    id_a = await _registrar(cliente_async, _USUARIO_A)
    await _registrar(cliente_async, _USUARIO_B)
    cabeceras_b = await _token(cliente_async, _USUARIO_B)

    respuesta = await cliente_async.patch(
        f"/api/v1/usuarios/{id_a}",
        json={"nombre": "Nombre Cambiado"},
        headers=cabeceras_b,
    )
    assert respuesta.status_code == 403
    assert respuesta.json()["error"] == "Solo puedes gestionar tu propia cuenta."


async def test_otro_usuario_no_puede_eliminar(cliente_async: AsyncClient) -> None:
    """DELETE sobre la cuenta de otro usuario devuelve 403."""
    id_a = await _registrar(cliente_async, _USUARIO_A)
    await _registrar(cliente_async, _USUARIO_B)
    cabeceras_b = await _token(cliente_async, _USUARIO_B)

    respuesta = await cliente_async.delete(f"/api/v1/usuarios/{id_a}", headers=cabeceras_b)
    assert respuesta.status_code == 403


async def test_otro_usuario_no_puede_restaurar(cliente_async: AsyncClient) -> None:
    """POST /restaurar sobre la cuenta de otro usuario devuelve 403."""
    id_a = await _registrar(cliente_async, _USUARIO_A)
    await _registrar(cliente_async, _USUARIO_B)
    cabeceras_b = await _token(cliente_async, _USUARIO_B)

    respuesta = await cliente_async.post(
        f"/api/v1/usuarios/{id_a}/restaurar",
        headers=cabeceras_b,
    )
    assert respuesta.status_code == 403


async def test_propietario_puede_modificar_su_cuenta(cliente_async: AsyncClient) -> None:
    """PATCH sobre la propia cuenta funciona (200)."""
    id_a = await _registrar(cliente_async, _USUARIO_A)
    cabeceras_a = await _token(cliente_async, _USUARIO_A)

    respuesta = await cliente_async.patch(
        f"/api/v1/usuarios/{id_a}",
        json={"nombre": "Usuario Uno Editado"},
        headers=cabeceras_a,
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Usuario Uno Editado"


async def test_propietario_puede_eliminar_su_cuenta(cliente_async: AsyncClient) -> None:
    """DELETE sobre la propia cuenta funciona (204)."""
    id_a = await _registrar(cliente_async, _USUARIO_A)
    cabeceras_a = await _token(cliente_async, _USUARIO_A)

    respuesta = await cliente_async.delete(f"/api/v1/usuarios/{id_a}", headers=cabeceras_a)
    assert respuesta.status_code == 204


async def test_modificar_usuario_inexistente_con_propietario_correcto(
    cliente_async: AsyncClient,
) -> None:
    """PATCH a un UUID inexistente con token: 403 solo si no es tu propio ID."""
    await _registrar(cliente_async, _USUARIO_A)
    cabeceras_a = await _token(cliente_async, _USUARIO_A)

    # UUID ajeno inexistente: 403 (no se revela si existe o no)
    respuesta = await cliente_async.patch(
        f"/api/v1/usuarios/{uuid.uuid4()}",
        json={"nombre": "Xx Yy"},
        headers=cabeceras_a,
    )
    assert respuesta.status_code == 403

    # El propio ID ya cubierto en test_propietario_puede_modificar_su_cuenta (404 si no existe)
