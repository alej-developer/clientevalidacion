"""
Repositorio específico para la entidad Usuario.

Hereda del RepositorioBase y añade consultas optimizadas
específicas del dominio de usuarios.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import obtener_logger
from app.modelos.usuario import Usuario
from app.repositorios.base import RepositorioBase

_logger = obtener_logger("repositorio.usuario")


class RepositorioUsuario(RepositorioBase[Usuario]):
    """
    Repositorio de acceso a datos para la entidad Usuario.

    Extiende las operaciones genéricas con consultas específicas
    optimizadas para el dominio de usuarios. Todas las búsquedas
    excluyen usuarios con soft delete aplicado salvo métodos explícitos.
    """

    def __init__(self, sesion: AsyncSession) -> None:
        super().__init__(modelo=Usuario, sesion=sesion)

    async def obtener_por_email(self, email: str) -> Usuario | None:
        """
        Busca un usuario activo por su dirección de correo electrónico.

        Excluye usuarios eliminados lógicamente.

        Args:
            email: Dirección de correo electrónico a buscar.

        Retorna:
            El usuario encontrado o None si no existe o está eliminado.
        """
        consulta = select(Usuario).where(
            Usuario.email == email.lower().strip(),
            self._filtro_no_eliminado(),
        )
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
        Verifica si un email ya está registrado por un usuario activo.

        Excluye registros eliminados lógicamente para permitir
        reutilizar emails de cuentas borradas.

        Args:
            email: Email a verificar.

        Retorna:
            True si el email ya existe en un usuario activo.
        """
        consulta = select(Usuario.id).where(
            Usuario.email == email.lower().strip(),
            self._filtro_no_eliminado(),
        )
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
        Lista solo los usuarios con cuentas activas (y no eliminados).

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

    async def buscar_usuarios(
        self,
        q: str | None = None,
        esta_activo: bool | None = None,
        ordenar_por: str = "creado_en",
        orden: str = "desc",
        pagina: int = 1,
        por_pagina: int = 20,
    ) -> tuple[list[Usuario], int]:
        """
        Búsqueda avanzada de usuarios con filtros por texto, estado y ordenación.

        Excluye usuarios eliminados lógicamente.

        Args:
            q: Término de búsqueda parcial en nombre o email.
            esta_activo: Filtrar por estado activo (True), inactivo (False) o ambos (None).
            ordenar_por: Campo por el que ordenar ('creado_en', 'nombre', 'email').
            orden: Dirección ('asc' o 'desc').
            pagina: Número de página (base 1).
            por_pagina: Cantidad de resultados por página.

        Retorna:
            Tupla (lista de usuarios coincidentes, total de registros).
        """
        from sqlalchemy import or_

        consulta = select(Usuario).where(self._filtro_no_eliminado())
        consulta_conteo = (
            select(func.count(Usuario.id)).select_from(Usuario).where(self._filtro_no_eliminado())
        )

        # Filtro de búsqueda por texto en nombre o email
        if q and q.strip():
            patron = f"%{q.strip().lower()}%"
            condicion_q = or_(
                Usuario.nombre.ilike(patron),
                Usuario.email.ilike(patron),
            )
            consulta = consulta.where(condicion_q)
            consulta_conteo = consulta_conteo.where(condicion_q)

        # Filtro por estado activo
        if esta_activo is not None:
            consulta = consulta.where(Usuario.esta_activo == esta_activo)
            consulta_conteo = consulta_conteo.where(Usuario.esta_activo == esta_activo)

        # Total
        resultado_conteo = await self.sesion.execute(consulta_conteo)
        total = resultado_conteo.scalar_one()

        # Ordenación
        columnas_permitidas = {
            "creado_en": Usuario.creado_en,
            "actualizado_en": Usuario.actualizado_en,
            "nombre": Usuario.nombre,
            "email": Usuario.email,
        }
        columna = columnas_permitidas.get(ordenar_por, Usuario.creado_en)
        if orden.lower() == "asc":
            consulta = consulta.order_by(columna.asc())
        else:
            consulta = consulta.order_by(columna.desc())

        # Paginación
        desplazamiento = (pagina - 1) * por_pagina
        consulta = consulta.offset(desplazamiento).limit(por_pagina)

        resultado = await self.sesion.execute(consulta)
        usuarios = list(resultado.scalars().all())

        _logger.debug(
            "Búsqueda avanzada de usuarios: q='%s', activo=%s, total=%d",
            q,
            esta_activo,
            total,
        )
        return usuarios, total

    async def obtener_eliminado_por_id(self, usuario_id: object) -> Usuario | None:
        """
        Obtiene un usuario eliminado lógicamente por su ID.

        Busca solo entre registros con eliminado_en IS NOT NULL,
        para el flujo de restauración.

        Args:
            usuario_id: UUID del usuario eliminado a buscar.

        Retorna:
            El usuario eliminado o None si no existe o está activo.
        """
        resultado = await self.sesion.get(Usuario, usuario_id)
        if resultado is None or not resultado.esta_eliminado:
            return None
        return resultado
