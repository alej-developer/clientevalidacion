"""
Módulo de logging centralizado y estructurado.

Configura el sistema de logging de Python con formato consistente,
niveles configurables desde variables de entorno y salida en consola
con colores para desarrollo y formato estructurado para producción.
"""

import logging
import sys
from typing import Final

# Formato para logs en desarrollo (legible por humanos)
_FORMATO_DESARROLLO: Final[str] = (
    "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
)

# Formato para logs en producción (estructurado)
_FORMATO_PRODUCCION: Final[str] = (
    '{"timestamp":"%(asctime)s","nivel":"%(levelname)s",'
    '"modulo":"%(name)s","funcion":"%(funcName)s",'
    '"linea":%(lineno)d,"mensaje":"%(message)s"}'
)


def configurar_logging(nivel: str = "INFO", es_debug: bool = False) -> None:
    """
    Configura el sistema de logging centralizado de la aplicación.

    Args:
        nivel: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        es_debug: Si es True, usa formato legible; si es False, formato JSON.
    """
    nivel_numerico = getattr(logging, nivel.upper(), logging.INFO)
    formato = _FORMATO_DESARROLLO if es_debug else _FORMATO_PRODUCCION

    # Configurar el formateador
    formateador = logging.Formatter(
        fmt=formato,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Configurar handler de consola
    handler_consola = logging.StreamHandler(stream=sys.stdout)
    handler_consola.setFormatter(formateador)
    handler_consola.setLevel(nivel_numerico)

    # Configurar el logger raíz de la aplicación
    logger_raiz = logging.getLogger("app")
    logger_raiz.setLevel(nivel_numerico)
    logger_raiz.handlers.clear()
    logger_raiz.addHandler(handler_consola)
    logger_raiz.propagate = False

    # Reducir ruido de librerías externas
    for nombre_logger in ("uvicorn", "uvicorn.access", "sqlalchemy.engine"):
        logger_externo = logging.getLogger(nombre_logger)
        logger_externo.setLevel(logging.WARNING)

    logger_raiz.info(
        "Sistema de logging configurado — nivel: %s, modo: %s",
        nivel,
        "desarrollo" if es_debug else "producción",
    )


def obtener_logger(nombre: str) -> logging.Logger:
    """
    Obtiene un logger hijo del logger principal de la aplicación.

    Args:
        nombre: Nombre del módulo o componente que solicita el logger.

    Retorna:
        Instancia de Logger configurada bajo el espacio 'app'.
    """
    return logging.getLogger(f"app.{nombre}")
