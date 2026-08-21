"""
Configuración del limitador de peticiones (Rate Limiting).

Utiliza slowapi para limitar la frecuencia de solicitudes
por dirección IP y proteger la API contra ataques de fuerza bruta y abusos.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import obtener_configuracion

_config = obtener_configuracion()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[_config.limite_por_defecto],
    headers_enabled=False,
)
