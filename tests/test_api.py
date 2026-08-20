"""
Pruebas de integración automatizadas para la API REST (/api/v1/usuarios).

Cubre:
- Endpoint de verificación de salud (/health).
- Flujo completo de creación exitosa (HTTP 201).
- Error por conflicto de email duplicado (HTTP 409).
- Error de validación de campos (HTTP 422).
- Búsqueda por ID exitosa (HTTP 200) y recurso no encontrado (HTTP 404).
- Listado paginado de usuarios (HTTP 200).
- Actualización parcial de usuario (HTTP 200).
- Eliminación de usuario (HTTP 204 y posterior 404).
"""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_verificar_salud(cliente_async: AsyncClient) -> None:
    """Verifica que el endpoint /health responda correctamente."""
    respuesta = await cliente_async.get("/health")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["estado"] == "ok"
    assert "version" in datos
    assert "timestamp" in datos


@pytest.mark.asyncio
async def test_crear_usuario_exitoso(cliente_async: AsyncClient) -> None:
    """Prueba el flujo exitoso de creación de usuario (HTTP 201)."""
    payload = {
        "nombre": "  Carlos  Mendoza  ",
        "email": "CARLOS.mendoza@ejemplo.com",
        "contrasena": "Password#123",
    }
    respuesta = await cliente_async.post("/api/v1/usuarios", json=payload)
    assert respuesta.status_code == 201

    datos = respuesta.json()
    assert datos["nombre"] == "Carlos Mendoza"
    assert datos["email"] == "carlos.mendoza@ejemplo.com"
    assert datos["esta_activo"] is True
    assert "id" in datos
    assert "creado_en" in datos
    assert "contrasena" not in datos
    assert "contrasena_hash" not in datos


@pytest.mark.asyncio
async def test_crear_usuario_error_email_duplicado(cliente_async: AsyncClient) -> None:
    """Verifica que no se permita registrar dos usuarios con el mismo email (HTTP 409)."""
    payload = {
        "nombre": "Ana Gómez",
        "email": "ana.gomez@ejemplo.com",
        "contrasena": "Password#123",
    }
    respuesta1 = await cliente_async.post("/api/v1/usuarios", json=payload)
    assert respuesta1.status_code == 201

    # Segundo intento con el mismo email
    respuesta2 = await cliente_async.post("/api/v1/usuarios", json=payload)
    assert respuesta2.status_code == 409
    datos_error = respuesta2.json()
    assert datos_error["exito"] is False
    assert "ya está registrado" in datos_error["error"]


@pytest.mark.asyncio
async def test_crear_usuario_error_validacion_422(cliente_async: AsyncClient) -> None:
    """Verifica que se rechacen datos inválidos con código 422."""
    # Email inválido
    payload_email_malo = {
        "nombre": "Ana Gómez",
        "email": "email_invalido",
        "contrasena": "Password#123",
    }
    respuesta1 = await cliente_async.post("/api/v1/usuarios", json=payload_email_malo)
    assert respuesta1.status_code == 422

    # Contraseña sin carácter especial
    payload_pass_debil = {
        "nombre": "Ana Gómez",
        "email": "ana@ejemplo.com",
        "contrasena": "Password123",
    }
    respuesta2 = await cliente_async.post("/api/v1/usuarios", json=payload_pass_debil)
    assert respuesta2.status_code == 422


@pytest.mark.asyncio
async def test_obtener_usuario_por_id(cliente_async: AsyncClient) -> None:
    """Prueba la recuperación de un usuario por su UUID (HTTP 200)."""
    payload = {
        "nombre": "Elena Torres",
        "email": "elena.torres@ejemplo.com",
        "contrasena": "Password#123",
    }
    respuesta_crear = await cliente_async.post("/api/v1/usuarios", json=payload)
    assert respuesta_crear.status_code == 201
    usuario_id = respuesta_crear.json()["id"]

    respuesta_obtener = await cliente_async.get(f"/api/v1/usuarios/{usuario_id}")
    assert respuesta_obtener.status_code == 200
    datos = respuesta_obtener.json()
    assert datos["id"] == usuario_id
    assert datos["nombre"] == "Elena Torres"


@pytest.mark.asyncio
async def test_obtener_usuario_no_encontrado_404(cliente_async: AsyncClient) -> None:
    """Verifica que consultar un UUID inexistente devuelva 404."""
    uuid_falso = str(uuid.uuid4())
    respuesta = await cliente_async.get(f"/api/v1/usuarios/{uuid_falso}")
    assert respuesta.status_code == 404
    datos_error = respuesta.json()
    assert datos_error["exito"] is False
    assert "No se encontró" in datos_error["error"]


@pytest.mark.asyncio
async def test_listar_usuarios_paginado(cliente_async: AsyncClient) -> None:
    """Prueba el listado paginado de usuarios (HTTP 200)."""
    # Crear 3 usuarios
    for i in range(1, 4):
        await cliente_async.post(
            "/api/v1/usuarios",
            json={
                "nombre": f"Usuario Pruebas {i}",
                "email": f"usuario{i}@ejemplo.com",
                "contrasena": "Password#123",
            },
        )

    respuesta = await cliente_async.get("/api/v1/usuarios?pagina=1&por_pagina=2")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["total"] == 3
    assert datos["pagina"] == 1
    assert datos["por_pagina"] == 2
    assert len(datos["elementos"]) == 2


@pytest.mark.asyncio
async def test_actualizar_usuario_parcial(cliente_async: AsyncClient) -> None:
    """Prueba la actualización parcial de un usuario con PATCH (HTTP 200)."""
    payload = {
        "nombre": "Roberto Ruiz",
        "email": "roberto.ruiz@ejemplo.com",
        "contrasena": "Password#123",
    }
    respuesta_crear = await cliente_async.post("/api/v1/usuarios", json=payload)
    usuario_id = respuesta_crear.json()["id"]

    # Actualizar solo el nombre
    payload_update = {"nombre": "Roberto Ruiz Actualizado"}
    respuesta_actualizar = await cliente_async.patch(
        f"/api/v1/usuarios/{usuario_id}", json=payload_update
    )
    assert respuesta_actualizar.status_code == 200
    datos = respuesta_actualizar.json()
    assert datos["nombre"] == "Roberto Ruiz Actualizado"
    assert datos["email"] == "roberto.ruiz@ejemplo.com"


@pytest.mark.asyncio
async def test_eliminar_usuario(cliente_async: AsyncClient) -> None:
    """Prueba la eliminación de un usuario (HTTP 204) y su posterior búsqueda (HTTP 404)."""
    payload = {
        "nombre": "Usuario Borrar",
        "email": "borrar@ejemplo.com",
        "contrasena": "Password#123",
    }
    respuesta_crear = await cliente_async.post("/api/v1/usuarios", json=payload)
    usuario_id = respuesta_crear.json()["id"]

    # Eliminar
    respuesta_eliminar = await cliente_async.delete(f"/api/v1/usuarios/{usuario_id}")
    assert respuesta_eliminar.status_code == 204

    # Verificar que ya no existe (404)
    respuesta_obtener = await cliente_async.get(f"/api/v1/usuarios/{usuario_id}")
    assert respuesta_obtener.status_code == 404
