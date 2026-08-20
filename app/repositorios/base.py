"""
Repositorio base genérico asíncrono.

Implementa el patrón Repository con operaciones CRUD genéricas
reutilizables por cualquier entidad del dominio. Usa tipado genérico
de Python 3.12+ para mantener la seguridad de tipos.
"""

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import obtener_logger
from app.db.base_class import ModeloBase

_logger = obtener_logger("repositorio.base")

T = TypeVar("T", bound=ModeloBase)


class RepositorioBase(Generic[T]):
    """
    Repositorio genérico asíncrono con operaciones CRUD estándar.

    Proporciona métodos reutilizables para cualquier modelo que
    herede de ModeloBase. Las subclases pueden sobrescribir o
    extender estos métodos con consultas específicas del dominio.

    Args:
        modelo: Clase del modelo SQLAlchemy asociado al repositorio.
        sesion: Sesión asíncrona de SQLAlchemy inyectada por dependencia.
    """

    def __init__(self, modelo: type[T], sesion: AsyncSession) -> None:
        self.modelo = modelo
        self.sesion = sesion

    async def obtener_por_id(self, registro_id: uuid.UUID) -> T | None:
        """
        Obtiene un registro por su identificador UUID.

        Args:
            registro_id: UUID del registro a buscar.

        Retorna:
            El registro encontrado o None si no existe.
        """
        resultado = await self.sesion.get(self.modelo, registro_id)
        _logger.debug(
            "Consulta por ID %s en %s — %s",
            registro_id,
            self.modelo.__tablename__,
            "encontrado" if resultado else "no encontrado",
        )
        return resultado

    async def listar_paginado(
        self,
        pagina: int = 1,
        por_pagina: int = 20,
        filtros: dict[str, Any] | None = None,
    ) -> tuple[list[T], int]:
        """
        Lista registros con paginación y filtros opcionales.

        Args:
            pagina: Número de página (empezando desde 1).
            por_pagina: Cantidad de registros por página.
            filtros: Diccionario de filtros {nombre_columna: valor}.

        Retorna:
            Tupla con (lista de registros, total de registros).
        """
        consulta = select(self.modelo)
        consulta_conteo = select(func.count()).select_from(self.modelo)

        # Aplicar filtros dinámicos
        if filtros:
            for campo, valor in filtros.items():
                if hasattr(self.modelo, campo) and valor is not None:
                    columna = getattr(self.modelo, campo)
                    consulta = consulta.where(columna == valor)
                    consulta_conteo = consulta_conteo.where(columna == valor)

        # Obtener total de registros
        resultado_conteo = await self.sesion.execute(consulta_conteo)
        total = resultado_conteo.scalar_one()

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
        Elimina un registro de la base de datos.

        Args:
            registro: Instancia del modelo a eliminar.
        """
        registro_id = registro.id
        await self.sesion.delete(registro)
        await self.sesion.flush()
        _logger.info(
            "Registro eliminado de %s con ID %s",
            self.modelo.__tablename__,
            registro_id,
        )
