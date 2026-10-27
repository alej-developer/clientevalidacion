"""
Tests de la vista pública sin PII (PR: lecturas abiertas sin email).

La API es pública a propósito (portafolio), pero las lecturas abiertas
no exponen emails: la vista completa solo la obtiene el propio usuario
autenticado. También cubre el seed de datos ficticios de la demo.
"""

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.usuario import Usuario
from scripts.seed_demo import USUARIOS_DEMO, sembrar_usuarios_demo

_USUARIO = {
    "nombre": "Vista Publica",
    "email": "vista.publica@ejemplo.com",
    "contrasena": "Password#123",
}


async def _registrar_y_token(cliente: AsyncClient) -> tuple[str, dict[str, str]]:
    respuesta = await cliente.post("/api/v1/usuarios", json=_USUARIO)
    assert respuesta.status_code == 201, respuesta.text
    usuario_id = str(respuesta.json()["id"])
    resp_login = await cliente.post(
        "/api/v1/auth/login",
        data={"username": _USUARIO["email"], "password": _USUARIO["contrasena"]},
    )
    return usuario_id, {"Authorization": f"Bearer {resp_login.json()['access_token']}"}


async def test_listado_no_expone_emails(cliente_async: AsyncClient) -> None:
    """GET /usuarios no devuelve email ni marcas de borrado."""
    await cliente_async.post("/api/v1/usuarios", json=_USUARIO)
    respuesta = await cliente_async.get("/api/v1/usuarios")
    assert respuesta.status_code == 200
    elementos = respuesta.json()["elementos"]
    assert len(elementos) == 1
    assert elementos[0]["nombre"] == _USUARIO["nombre"]
    assert "email" not in elementos[0]
    assert "eliminado_en" not in elementos[0]
    assert "contrasena" not in elementos[0]


async def test_detalle_anonimo_sin_email(cliente_async: AsyncClient) -> None:
    """GET /usuarios/{id} sin token devuelve la vista pública."""
    respuesta = await cliente_async.post("/api/v1/usuarios", json=_USUARIO)
    usuario_id = respuesta.json()["id"]
    detalle = await cliente_async.get(f"/api/v1/usuarios/{usuario_id}")
    assert detalle.status_code == 200
    assert detalle.json()["nombre"] == _USUARIO["nombre"]
    assert "email" not in detalle.json()


async def test_detalle_propietario_con_email(cliente_async: AsyncClient) -> None:
    """El propio usuario con su token ve su detalle completo (con email)."""
    usuario_id, cabeceras = await _registrar_y_token(cliente_async)
    detalle = await cliente_async.get(f"/api/v1/usuarios/{usuario_id}", headers=cabeceras)
    assert detalle.status_code == 200
    assert detalle.json()["email"] == _USUARIO["email"]


async def test_detalle_con_token_ajeno_sigue_siendo_publico(cliente_async: AsyncClient) -> None:
    """Un token de OTRO usuario no revela el email del detalle."""
    usuario_id, _ = await _registrar_y_token(cliente_async)
    otro = {"nombre": "Otro Usuario", "email": "otro@ejemplo.com", "contrasena": "Password#456"}
    await cliente_async.post("/api/v1/usuarios", json=otro)
    resp_login = await cliente_async.post(
        "/api/v1/auth/login",
        data={"username": otro["email"], "password": otro["contrasena"]},
    )
    cabeceras_otro = {"Authorization": f"Bearer {resp_login.json()['access_token']}"}
    detalle = await cliente_async.get(f"/api/v1/usuarios/{usuario_id}", headers=cabeceras_otro)
    assert detalle.status_code == 200
    assert "email" not in detalle.json()


async def test_auth_yo_sigue_devolviendo_email(cliente_async: AsyncClient) -> None:
    """GET /auth/yo mantiene la vista completa del propio usuario."""
    _, cabeceras = await _registrar_y_token(cliente_async)
    respuesta = await cliente_async.get("/api/v1/auth/yo", headers=cabeceras)
    assert respuesta.status_code == 200
    assert respuesta.json()["email"] == _USUARIO["email"]


async def test_seed_demo_es_idempotente(
    cliente_async: AsyncClient,
    sesion_db: AsyncSession,
) -> None:
    """El seed crea los usuarios ficticios una sola vez (omite existentes)."""
    creados, existentes = await sembrar_usuarios_demo(sesion_db)
    assert (creados, existentes) == (len(USUARIOS_DEMO), 0)
    await sesion_db.commit()

    total = (await sesion_db.execute(select(func.count()).select_from(Usuario))).scalar_one()
    assert total == len(USUARIOS_DEMO)

    # Segunda pasada: no crea nada
    creados2, existentes2 = await sembrar_usuarios_demo(sesion_db)
    assert (creados2, existentes2) == (0, len(USUARIOS_DEMO))
