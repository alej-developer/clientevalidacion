"""
Servicio de autenticación: ciclo de vida de los refresh tokens.

Emisión, rotación y revocación de refresh tokens opacos persistidos
por su hash SHA-256. La rotación invalida el token presentado y emite
uno nuevo; un token revocado, expirado o desconocido se rechaza con 401.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import obtener_configuracion
from app.core.excepciones.excepciones import NoAutorizadoError
from app.core.seguridad import crear_refresh_token, hashear_refresh_token
from app.modelos.refresh_token import RefreshToken

_config = obtener_configuracion()


class ServicioAutenticacion:
    """Lógica de negocio de los refresh tokens."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def emitir_refresh(self, usuario_id: uuid.UUID) -> str:
        """
        Emite un refresh token nuevo para el usuario y lo persiste (hash).

        Args:
            usuario_id: UUID del usuario autenticado.

        Retorna:
            El refresh token en claro (única vez que está disponible).
        """
        token = crear_refresh_token()
        fila = RefreshToken(
            usuario_id=usuario_id,
            token_hash=hashear_refresh_token(token),
            expira_en=datetime.now(tz=UTC) + timedelta(days=_config.jwt_refresh_expiracion_dias),
        )
        self._sesion.add(fila)
        await self._sesion.commit()
        return token

    async def _buscar(self, token: str) -> RefreshToken:
        """Localiza un refresh token por su valor en claro o lanza 401."""
        resultado = await self._sesion.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == hashear_refresh_token(token),
                RefreshToken.eliminado_en.is_(None),
            )
        )
        fila = resultado.scalar_one_or_none()
        if fila is None:
            raise NoAutorizadoError(mensaje="Refresh token inválido.")
        return fila

    @staticmethod
    def _validar_vigente(fila: RefreshToken) -> None:
        """Rechaza tokens revocados o expirados."""
        if fila.revocado:
            # Reutilización de un token ya rotado o revocado.
            raise NoAutorizadoError(mensaje="Refresh token revocado.")
        expira = fila.expira_en
        if expira.tzinfo is None:  # SQLite devuelve datetimes naive
            expira = expira.replace(tzinfo=UTC)
        if expira <= datetime.now(tz=UTC):
            raise NoAutorizadoError(mensaje="Refresh token expirado.")

    async def rotar_refresh(self, token: str) -> tuple[uuid.UUID, str]:
        """
        Rota un refresh token: valida el presentado, lo revoca y emite otro.

        Args:
            token: Refresh token en claro (del cuerpo o de la cookie).

        Retorna:
            Tupla (usuario_id, nuevo refresh token en claro).

        Raises:
            NoAutorizadoError: Si el token no existe, está revocado o expiró.
        """
        fila = await self._buscar(token)
        self._validar_vigente(fila)

        nuevo_token = crear_refresh_token()
        nueva_fila = RefreshToken(
            usuario_id=fila.usuario_id,
            token_hash=hashear_refresh_token(nuevo_token),
            expira_en=fila.expira_en,  # la rotación conserva la expiración absoluta
        )
        self._sesion.add(nueva_fila)
        await self._sesion.flush()

        fila.revocado = True
        fila.reemplazado_por = nueva_fila.id
        await self._sesion.commit()
        return fila.usuario_id, nuevo_token

    async def revocar_refresh(self, token: str) -> None:
        """
        Revoca un refresh token (logout). Ignora tokens desconocidos:
        cerrar sesión es idempotente y no debe filtrar si un token existe.
        """
        resultado = await self._sesion.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == hashear_refresh_token(token),
                RefreshToken.eliminado_en.is_(None),
            )
        )
        fila = resultado.scalar_one_or_none()
        if fila is not None and not fila.revocado:
            fila.revocado = True
            await self._sesion.commit()
