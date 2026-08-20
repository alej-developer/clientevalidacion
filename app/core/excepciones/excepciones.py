"""
Manejadores globales de excepciones para la aplicación.

Define excepciones de dominio personalizadas y el middleware
que captura errores no controlados, devolviendo respuestas
JSON consistentes al cliente.
"""

from typing import Any


class ExcepcionBase(Exception):
    """Excepción base de la aplicación con código de estado y detalle."""

    def __init__(
        self,
        mensaje: str = "Error interno del servidor",
        codigo_estado: int = 500,
        detalles: dict[str, Any] | None = None,
    ) -> None:
        self.mensaje = mensaje
        self.codigo_estado = codigo_estado
        self.detalles = detalles or {}
        super().__init__(self.mensaje)


class NoEncontradoError(ExcepcionBase):
    """Recurso no encontrado (HTTP 404)."""

    def __init__(
        self,
        mensaje: str = "Recurso no encontrado",
        detalles: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(mensaje=mensaje, codigo_estado=404, detalles=detalles)


class ValidacionError(ExcepcionBase):
    """Error de validación de datos de entrada (HTTP 422)."""

    def __init__(
        self,
        mensaje: str = "Error de validación",
        detalles: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(mensaje=mensaje, codigo_estado=422, detalles=detalles)


class ConflictoError(ExcepcionBase):
    """Conflicto con el estado actual del recurso (HTTP 409)."""

    def __init__(
        self,
        mensaje: str = "Conflicto con el recurso",
        detalles: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(mensaje=mensaje, codigo_estado=409, detalles=detalles)


class NoAutorizadoError(ExcepcionBase):
    """Acceso no autorizado (HTTP 401)."""

    def __init__(
        self,
        mensaje: str = "No autorizado",
        detalles: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(mensaje=mensaje, codigo_estado=401, detalles=detalles)


class ProhibidoError(ExcepcionBase):
    """Acceso prohibido (HTTP 403)."""

    def __init__(
        self,
        mensaje: str = "Acceso prohibido",
        detalles: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(mensaje=mensaje, codigo_estado=403, detalles=detalles)
