"""
Middleware de captura global de excepciones.

Intercepta todas las excepciones no controladas y las excepciones
de dominio (ExcepcionBase), transformándolas en respuestas JSON
consistentes con la estructura estándar de error de la API.
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.excepciones.excepciones import ExcepcionBase
from app.core.logging import obtener_logger

_logger = obtener_logger("middleware.excepciones")


class MiddlewareExcepciones(BaseHTTPMiddleware):
    """Middleware que captura y normaliza todas las excepciones en respuestas JSON."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """
        Procesa la petición y captura cualquier excepción no controlada.

        Args:
            request: Petición HTTP entrante.
            call_next: Siguiente middleware o handler en la cadena.

        Retorna:
            Respuesta HTTP, ya sea la original o una respuesta de error JSON.
        """
        try:
            respuesta: Response = await call_next(request)
            return respuesta

        except ExcepcionBase as exc:
            _logger.warning(
                "Excepción de dominio — %s %s — %d: %s",
                request.method,
                request.url.path,
                exc.codigo_estado,
                exc.mensaje,
            )
            return JSONResponse(
                status_code=exc.codigo_estado,
                content={
                    "exito": False,
                    "error": exc.mensaje,
                    "detalles": exc.detalles,
                },
            )

        except Exception as exc:
            _logger.error(
                "Excepción no controlada — %s %s — %s: %s",
                request.method,
                request.url.path,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "exito": False,
                    "error": "Error interno del servidor",
                    "detalles": {},
                },
            )
