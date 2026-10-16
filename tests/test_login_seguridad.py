"""
Tests de seguridad del login y del registro (PR: anti-enumeración + rate limit).

Verifica que el login devuelve exactamente la misma respuesta (código 401
y cuerpo) para email inexistente, contraseña incorrecta y cuenta
desactivada, y que el registro tiene límite de tasa propio (429).
"""

from httpx import AsyncClient

_USUARIO = {
    "nombre": "Usuario Seguridad",
    "email": "seguridad@ejemplo.com",
    "contrasena": "Password#123",
}


async def _crear_usuario(cliente: AsyncClient) -> None:
    respuesta = await cliente.post("/api/v1/usuarios", json=_USUARIO)
    assert respuesta.status_code == 201, respuesta.text


async def _login(cliente: AsyncClient, email: str, contrasena: str) -> tuple[int, dict]:
    respuesta = await cliente.post(
        "/api/v1/auth/login",
        data={"username": email, "password": contrasena},
    )
    return respuesta.status_code, respuesta.json()


async def test_login_email_inexistente_devuelve_401_generico(cliente_async: AsyncClient) -> None:
    """Email no registrado: 401 con el mensaje genérico (no 404 ni 422)."""
    codigo, cuerpo = await _login(cliente_async, "nadie@ejemplo.com", "Password#123")
    assert codigo == 401
    assert cuerpo == {"exito": False, "error": "Credenciales inválidas.", "detalles": {}}


async def test_login_contrasena_incorrecta_mismo_401(cliente_async: AsyncClient) -> None:
    """Contraseña incorrecta: mismo 401 y mismo cuerpo que con email inexistente."""
    await _crear_usuario(cliente_async)
    codigo, cuerpo = await _login(cliente_async, _USUARIO["email"], "MalPassword#999")
    assert codigo == 401
    assert cuerpo == {"exito": False, "error": "Credenciales inválidas.", "detalles": {}}


async def test_login_cuenta_desactivada_mismo_401(
    cliente_async: AsyncClient,
    sesion_db,
) -> None:
    """Cuenta desactivada: mismo 401 genérico (no revela el estado de la cuenta)."""
    await _crear_usuario(cliente_async)
    from app.repositorios.usuario import RepositorioUsuario

    repositorio = RepositorioUsuario(sesion=sesion_db)
    usuario = await repositorio.obtener_por_email(_USUARIO["email"])
    assert usuario is not None
    usuario.esta_activo = False
    await sesion_db.commit()

    codigo, cuerpo = await _login(cliente_async, _USUARIO["email"], _USUARIO["contrasena"])
    assert codigo == 401
    assert cuerpo == {"exito": False, "error": "Credenciales inválidas.", "detalles": {}}


async def test_login_correcto_sigue_funcionando(cliente_async: AsyncClient) -> None:
    """El login válido no se ve afectado por el cambio."""
    await _crear_usuario(cliente_async)
    codigo, cuerpo = await _login(cliente_async, _USUARIO["email"], _USUARIO["contrasena"])
    assert codigo == 200
    assert "access_token" in cuerpo


async def test_email_con_puntos_consecutivos_rechazado(cliente_async: AsyncClient) -> None:
    """EmailStr rechaza formatos que la regex casera anterior aceptaba (p. ej. 'a@b..com')."""
    respuesta = await cliente_async.post(
        "/api/v1/usuarios",
        json={**_USUARIO, "email": "a@b..com"},
    )
    assert respuesta.status_code == 422


async def test_registro_tiene_limite_de_tasa(cliente_async: AsyncClient) -> None:
    """El registro aplica el límite estricto (10/minuto): la 11.ª petición devuelve 429."""
    codigos = []
    for i in range(11):
        respuesta = await cliente_async.post(
            "/api/v1/usuarios",
            json={
                "nombre": f"Usuario Limite {i}",
                "email": f"limite{i}@ejemplo.com",
                "contrasena": "Password#123",
            },
        )
        codigos.append(respuesta.status_code)
    assert codigos[:10] == [201] * 10
    assert codigos[10] == 429
