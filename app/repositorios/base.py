"""
Repositorio base genérico asíncrono con soporte de Soft Delete.

Implementa el patrón Repository con operaciones CRUD genéricas
reutilizables por cualquier entidad del dominio. Todas las consultas
filtran automáticamente los registros borrados lógicamente
(eliminado_en IS NULL), preservando los datos para auditoría.
"""

import uuid
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import obtener_logger
from app.db.base_class import ModeloBase

_logger = obtener_logger("repositorio.base")

T = TypeVar("T", bound=ModeloBase)


class RepositorioBase(Generic[T]):
    """
    Repositorio genérico asíncrono con operaciones CRUD y Soft Delete.

    Todas las consultas de listado y búsqueda excluyen automáticamente
    registros con eliminado_en IS NOT NULL. El método 'eliminar' realiza
    un borrado lógico en vez de físico.

    Args:
        modelo: Clase del modelo SQLAlchemy asociado al repositorio.
        sesion: Sesión asíncrona de SQLAlchemy inyectada por dependencia.
    """

    def __init__(self, modelo: type[T], sesion: AsyncSession) -> None:
        self.modelo = modelo
        self.sesion = sesion

    def _filtro_no_eliminado(self) -> Any:
        """Condición SQLAlchemy para excluir registros borrados lógicamente."""
        return self.modelo.eliminado_en.is_(None)  # type: ignore[union-attr]

    async def obtener_por_id(self, registro_id: uuid.UUID) -> T | None:
        """
        Obtiene un registro activo (no eliminado) por su identificador UUID.

        Args:
            registro_id: UUID del registro a buscar.

        Retorna:
            El registro encontrado o None si no existe o está eliminado.
        """
        consulta = select(self.modelo).where(
            self.modelo.id == registro_id,
            self._filtro_no_eliminado(),
        )
        resultado = await self.sesion.execute(consulta)
        registro = resultado.scalar_one_or_none()
        _logger.debug(
            "Consulta por ID %s en %s — %s",
            registro_id,
            self.modelo.__tablename__,
            "encontrado" if registro else "no encontrado",
        )
        return registro

    async def listar_paginado(
        self,
        pagina: int = 1,
        por_pagina: int = 20,
        filtros: dict[str, Any] | None = None,
        ordenar_por: str = "creado_en",
        orden: str = "desc",
    ) -> tuple[list[T], int]:
        """
        Lista registros activos con paginación, filtros y ordenación.

        Excluye automáticamente los registros con soft delete aplicado.

        Args:
            pagina: Número de página (empezando desde 1).
            por_pagina: Cantidad de registros por página.
            filtros: Diccionario de filtros {nombre_columna: valor}.
            ordenar_por: Nombre de la columna para ordenar.
            orden: Dirección de orden ('asc' o 'desc').

        Retorna:
            Tupla con (lista de registros, total de registros activos).
        """
        consulta = select(self.modelo).where(self._filtro_no_eliminado())
        consulta_conteo = (
            select(func.count()).select_from(self.modelo).where(self._filtro_no_eliminado())
        )

        # Aplicar filtros dinámicos adicionales
        if filtros:
            for campo, valor in filtros.items():
                if hasattr(self.modelo, campo) and valor is not None:
                    columna = getattr(self.modelo, campo)
                    consulta = consulta.where(columna == valor)
                    consulta_conteo = consulta_conteo.where(columna == valor)

        # Obtener total de registros
        resultado_conteo = await self.sesion.execute(consulta_conteo)
        total = resultado_conteo.scalar_one()

        # Aplicar ordenación
        if hasattr(self.modelo, ordenar_por):
            columna_orden = getattr(self.modelo, ordenar_por)
            if orden.lower() == "asc":
                consulta = consulta.order_by(columna_orden.asc())
            else:
                consulta = consulta.order_by(columna_orden.desc())

        # Aplicar paginación
        desplazamiento = (pagina - 1) * por_pagina
        consulta = consulta.offset(desplazamiento).limit(por_pagina)

        # Ejecutar consulta paginada
        resultado = await self.sesion.execute(consulta)
        registros = list(resultado.scalars().all())

        _logger.debug(
            "Listado paginado de %s — página %d, %d registros de %d totales",
            self.modelo.__tablename__,
            pagina,
            len(registros),
            total,
        )
        return registros, total

    async def crear(self, datos: dict[str, Any]) -> T:
        """
        Crea un nuevo registro en la base de datos.

        Args:
            datos: Diccionario con los valores de los campos del registro.

        Retorna:
            El registro recién creado con su ID asignado.
        """
        registro = self.modelo(**datos)
        self.sesion.add(registro)
        await self.sesion.flush()
        await self.sesion.refresh(registro)
        _logger.info(
            "Registro creado en %s con ID %s",
            self.modelo.__tablename__,
            registro.id,
        )
        return registro

    async def actualizar(self, registro: T, datos: dict[str, Any]) -> T:
        """
        Actualiza un registro existente con los datos proporcionados.

        Solo actualiza los campos incluidos en el diccionario de datos,
        ignorando valores None para permitir actualizaciones parciales.

        Args:
            registro: Instancia del modelo a actualizar.
            datos: Diccionario con los campos y nuevos valores.

        Retorna:
            El registro actualizado.
        """
        for campo, valor in datos.items():
            if valor is not None and hasattr(registro, campo):
                setattr(registro, campo, valor)
        await self.sesion.flush()
        await self.sesion.refresh(registro)
        _logger.info(
            "Registro actualizado en %s con ID %s — campos: %s",
            self.modelo.__tablename__,
            registro.id,
            list(datos.keys()),
        )
        return registro

    async def eliminar(self, registro: T) -> None:
        """
        Realiza un borrado lógico (Soft Delete) del registro.

        Establece eliminado_en al timestamp actual en vez de eliminar
        la fila de la base de datos, preservando los datos para auditoría.

        Args:
            registro: Instancia del modelo a marcar como eliminada.
        """
        registro_id = registro.id
        registro.eliminado_en = datetime.now(tz=UTC)  # type: ignore[assignment]
        await self.sesion.flush()
        _logger.info(
            "Soft delete aplicado en %s con ID %s",
            self.modelo.__tablename__,
            registro_id,
        )

    async def restaurar(self, registro: T) -> T:
        """
        Restaura un registro previamente eliminado lógicamente.

        Establece eliminado_en a None, haciendo el registro visible
        de nuevo en todas las consultas estándar.

        Args:
            registro: Instancia del modelo a restaurar.

        Retorna:
            El registro restaurado.
        """
        registro_id = registro.id
        registro.eliminado_en = None  # type: ignore[assignment]
        await self.sesion.flush()
        await self.sesion.refresh(registro)
        _logger.info(
            "Registro restaurado en %s con ID %s",
            self.modelo.__tablename__,
            registro_id,
        )
        return registro

    async def obtener_por_id_incluyendo_eliminados(self, registro_id: uuid.UUID) -> T | None:
        """
        Obtiene un registro por ID sin filtrar eliminados.

        Útil para operaciones de restauración o auditoría.

        Args:
            registro_id: UUID del registro a buscar.

        Retorna:
            El registro (activo o eliminado) o None si no existe.
        """
        resultado = await self.sesion.get(self.modelo, registro_id)
        return resultado
