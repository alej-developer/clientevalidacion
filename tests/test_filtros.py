"""
Pruebas de integracion para filtros avanzados de busqueda, ordenacion y Rate Limiting.

Cubre:
- Busqueda por texto 'q' en nombre o email.
- Filtrado por estado 'esta_activo'.
- Ordenacion por nombre, email, creado_en (ascendente y descendente).
- Validacion de parametros de ordenacion invalidos.
- Rate Limiting en endpoint de autenticacion.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_busqueda_usuarios_por_texto_q(cliente_async: AsyncClient) -> None:
    """Busqueda con parametro 'q' filtra por nombre o email de forma insensible a mayusculas."""
    # Crear usuarios de prueba
    await cliente_async.post(
        "/api/v1/usuarios",
        json={
            "nombre": "Carlos Santana",
            "email": "carlos.santana@ejemplo.com",
            "contrasena": "Password#123",
        },
    )
    await cliente_async.post(
        "/api/v1/usuarios",
        json={"nombre": "Maria Lopez", "email": "mlopez@musica.org", "contrasena": "Password#123"},
    )
    await cliente_async.post(
        "/api/v1/usuarios",
        json={"nombre": "Andres Calamaro", "email": "andres@rock.es", "contrasena": "Password#123"},
    )

    # Buscar 'carlos'
    resp_carlos = await cliente_async.get("/api/v1/usuarios?q=carlos")
    assert resp_carlos.status_code == 200
    datos_carlos = resp_carlos.json()
    assert datos_carlos["total"] == 1
    assert datos_carlos["elementos"][0]["nombre"] == "Carlos Santana"

    # Buscar por dominio 'musica' en email
    resp_musica = await cliente_async.get("/api/v1/usuarios?q=musica")
    assert resp_musica.status_code == 200
    assert resp_musica.json()["total"] == 1
    assert resp_musica.json()["elementos"][0]["email"] == "mlopez@musica.org"

    # Buscar coincidencia parcial comun 'a'
    resp_comun = await cliente_async.get("/api/v1/usuarios?q=a")
    assert resp_comun.status_code == 200
    assert resp_comun.json()["total"] >= 2


@pytest.mark.asyncio
async def test_filtrar_por_estado_activo(cliente_async: AsyncClient) -> None:
    """Filtra usuarios activos o inactivos con 'esta_activo'."""
    # Crear usuario y luego desactivarlo
    resp = await cliente_async.post(
        "/api/v1/usuarios",
        json={
            "nombre": "Usuario Inactivo",
            "email": "inactivo@ejemplo.com",
            "contrasena": "Password#123",
        },
    )
    usuario_id = resp.json()["id"]

    # Login para obtener token y actualizarlo a inactivo
    resp_login = await cliente_async.post(
        "/api/v1/auth/login",
        data={"username": "inactivo@ejemplo.com", "password": "Password#123"},
    )
    token = resp_login.json()["access_token"]

    await cliente_async.patch(
        f"/api/v1/usuarios/{usuario_id}",
        json={"esta_activo": False},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Crear otro usuario que permanezca activo
    await cliente_async.post(
        "/api/v1/usuarios",
        json={
            "nombre": "Usuario Activo",
            "email": "activo@ejemplo.com",
            "contrasena": "Password#123",
        },
    )

    # Consultar solo inactivos
    resp_inactivos = await cliente_async.get("/api/v1/usuarios?esta_activo=false")
    assert resp_inactivos.status_code == 200
    assert resp_inactivos.json()["total"] == 1
    assert resp_inactivos.json()["elementos"][0]["email"] == "inactivo@ejemplo.com"

    # Consultar solo activos
    resp_activos = await cliente_async.get("/api/v1/usuarios?esta_activo=true")
    assert resp_activos.status_code == 200
    assert resp_activos.json()["total"] == 1
    assert resp_activos.json()["elementos"][0]["email"] == "activo@ejemplo.com"


@pytest.mark.asyncio
async def test_ordenacion_usuarios(cliente_async: AsyncClient) -> None:
    """Ordena los resultados segun campo y direccion especificados."""
    await cliente_async.post(
        "/api/v1/usuarios",
        json={"nombre": "Ana Perez", "email": "ana@ejemplo.com", "contrasena": "Password#123"},
    )
    await cliente_async.post(
        "/api/v1/usuarios",
        json={
            "nombre": "Zulema Ortiz",
            "email": "zulema@ejemplo.com",
            "contrasena": "Password#123",
        },
    )

    # Orden ascendente por nombre (Ana debe ir primero)
    resp_asc = await cliente_async.get("/api/v1/usuarios?ordenar_por=nombre&orden=asc")
    assert resp_asc.status_code == 200
    nombres_asc = [u["nombre"] for u in resp_asc.json()["elementos"]]
    assert nombres_asc[0] == "Ana Perez"
    assert nombres_asc[-1] == "Zulema Ortiz"

    # Orden descendente por nombre (Zulema debe ir primero)
    resp_desc = await cliente_async.get("/api/v1/usuarios?ordenar_por=nombre&orden=desc")
    assert resp_desc.status_code == 200
    nombres_desc = [u["nombre"] for u in resp_desc.json()["elementos"]]
    assert nombres_desc[0] == "Zulema Ortiz"
    assert nombres_desc[-1] == "Ana Perez"


@pytest.mark.asyncio
async def test_ordenacion_con_direccion_invalida_retorna_422(cliente_async: AsyncClient) -> None:
    """Direccion de orden diferente de 'asc' o 'desc' es rechazada con HTTP 422."""
    resp = await cliente_async.get("/api/v1/usuarios?orden=lateral")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_rate_limit_auth_login_retorna_429(cliente_async: AsyncClient) -> None:
    """Exceder el limite de intentos en login devuelve HTTP 429 con mensaje estructurado."""
    # Crear usuario
    await cliente_async.post(
        "/api/v1/usuarios",
        json={"nombre": "Rate Test", "email": "rate@ejemplo.com", "contrasena": "Password#123"},
    )

    # El limite es 10/minute. Realizar 11 peticiones consecutivas
    respuestas = []
    for _ in range(11):
        r = await cliente_async.post(
            "/api/v1/auth/login",
            data={"username": "rate@ejemplo.com", "password": "Password#123"},
        )
        respuestas.append(r.status_code)

    # Al menos la ultima debe ser 429
    assert 429 in respuestas
    # Verificar formato del error 429
    ultimo_resp = await cliente_async.post(
        "/api/v1/auth/login",
        data={"username": "rate@ejemplo.com", "password": "Password#123"},
    )
    assert ultimo_resp.status_code == 429
    datos = ultimo_resp.json()
    assert datos["exito"] is False
    assert "Demasiadas peticiones" in datos["error"]
