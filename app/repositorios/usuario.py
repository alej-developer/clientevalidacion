"""
Repositorio específico para la entidad Usuario.

Hereda del RepositorioBase y añade consultas optimizadas
específicas del dominio de usuarios.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import obtener_logger
from app.modelos.usuario import Usuario
from app.repositorios.base import RepositorioBase

_logger = obtener_logger("repositorio.usuario")


class RepositorioUsuario(RepositorioBase[Usuario]):
    """
    Repositorio de acceso a datos para la entidad Usuario.

    Extiende las operaciones genéricas con consultas específicas
    optimizadas para el dominio de usuarios.
    """

    def __init__(self, sesion: AsyncSession) -> None:
        super().__init__(modelo=Usuario, sesion=sesion)

    async def obtener_por_email(self, email: str) -> Usuario | None:
        """
        Busca un usuario por su dirección de correo electrónico.

        Utiliza el índice único sobre la columna 'email' para
        garantizar una búsqueda eficiente O(1).

        Args:
            email: Dirección de correo electrónico a buscar.

        Retorna:
            El usuario encontrado o None si no existe.
        """
        consulta = select(Usuario).where(Usuario.email == email.lower().strip())
        resultado = await self.sesion.execute(consulta)
        usuario = resultado.scalar_one_or_none()
        _logger.debug(
            "Búsqueda por email '%s' — %s",
            email,
            "encontrado" if usuario else "no encontrado",
        )
        return usuario

    async def existe_email(self, email: str) -> bool:
        """
        Verifica si un email ya está registrado en el sistema.

        Consulta optimizada que solo verifica existencia sin cargar
        toda la entidad.

        Args:
            email: Email a verificar.

        Retorna:
            True si el email ya existe, False en caso contrario.
        """
        consulta = select(Usuario.id).where(Usuario.email == email.lower().strip())
        resultado = await self.sesion.execute(consulta)
        existe = resultado.scalar_one_or_none() is not None
        _logger.debug("Verificación de existencia para email '%s': %s", email, existe)
        return existe

    async def listar_activos(
        self,
        pagina: int = 1,
        por_pagina: int = 20,
    ) -> tuple[list[Usuario], int]:
        """
        Lista solo los usuarios con cuentas activas.

        Utiliza el índice compuesto 'ix_usuarios_email_activo' para
        optimizar la consulta filtrada.

        Args:
            pagina: Número de página.
            por_pagina: Cantidad de registros por página.

        Retorna:
            Tupla con (lista de usuarios activos, total de activos).
        """
        return await self.listar_paginado(
            pagina=pagina,
            por_pagina=por_pagina,
            filtros={"esta_activo": True},
        )
