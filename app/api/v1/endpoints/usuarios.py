"""
Endpoints RESTful para la gestión de usuarios (/api/v1/usuarios).

Controladores HTTP versionados v1 con códigos de estado semánticos,
paginación, filtros tipados, documentación OpenAPI y respuestas tipadas.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, status

from app.api.deps import obtener_servicio_usuario, obtener_usuario_actual
from app.core.config import obtener_configuracion
from app.core.excepciones.excepciones import ProhibidoError
from app.core.limiter import limiter
from app.esquemas.usuario import (
    ActualizarUsuario,
    CrearUsuario,
    RespuestaListaUsuarios,
    RespuestaUsuario,
)
from app.servicios.usuario import ServicioUsuario

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

_config = obtener_configuracion()


def _verificar_propiedad(usuario_id: uuid.UUID, usuario_actual: RespuestaUsuario) -> None:
    """
    Exige que el usuario autenticado actúe sobre su propia cuenta.

    Autorización por propiedad: cada usuario solo puede modificar, borrar
    o restaurar su propio registro. Punto de extensión para un futuro
    rol administrador que pueda operar sobre cualquier cuenta.

    Args:
        usuario_id: UUID del usuario objetivo de la operación.
        usuario_actual: Usuario autenticado dueño del token JWT.

    Raises:
        ProhibidoError: Si el objetivo no es la propia cuenta (HTTP 403).
    """
    if usuario_actual.id != usuario_id:
        raise ProhibidoError(mensaje="Solo puedes gestionar tu propia cuenta.")


@router.post(
    "",
    response_model=RespuestaUsuario,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo usuario",
    description=(
        "Registra un nuevo usuario en el sistema. Realiza validaciones estrictas "
        "de formato de email y complejidad de contraseña. La contraseña se almacena "
        "de forma segura mediante hash PBKDF2-SHA256."
    ),
    responses={
        201: {"description": "Usuario creado exitosamente"},
        400: {"description": "Petición incorrecta o datos inválidos"},
        409: {"description": "Conflicto: El email ya está registrado"},
        422: {"description": "Error de validación en los campos enviados"},
        429: {"description": "Demasiadas peticiones consecutivas (Rate Limit)"},
    },
)
@limiter.limit(_config.limite_auth)
async def crear_usuario(
    request: Request,
    datos: CrearUsuario,
    servicio: Annotated[ServicioUsuario, Depends(obtener_servicio_usuario)],
) -> RespuestaUsuario:
    """Crea un usuario en el sistema."""
    return await servicio.crear_usuario(datos)


@router.get(
    "",
    response_model=RespuestaListaUsuarios,
    status_code=status.HTTP_200_OK,
    summary="Listar usuarios paginados",
    description=(
        "Devuelve un listado paginado de usuarios con soporte para búsqueda por texto "
        "(nombre o email), filtrado por estado de activación y ordenación personalizada."
    ),
    responses={
        200: {"description": "Lista de usuarios recuperada exitosamente"},
        422: {"description": "Parámetros de consulta o paginación inválidos"},
    },
)
async def listar_usuarios(
    servicio: Annotated[ServicioUsuario, Depends(obtener_servicio_usuario)],
    pagina: Annotated[
        int,
        Query(ge=1, description="Número de página a consultar (mínimo 1)"),
    ] = 1,
    por_pagina: Annotated[
        int,
        Query(ge=1, le=100, description="Cantidad de registros por página (1-100)"),
    ] = 20,
    q: Annotated[
        str | None,
        Query(
            description="Búsqueda por texto en nombre o email",
            min_length=1,
            max_length=100,
        ),
    ] = None,
    esta_activo: Annotated[
        bool | None,
        Query(description="Filtrar por estado activo (True), inactivo (False) o ambos (None)"),
    ] = None,
    ordenar_por: Annotated[
        str,
        Query(
            description="Campo para ordenar resultados (creado_en, actualizado_en, nombre, email)"
        ),
    ] = "creado_en",
    orden: Annotated[
        str,
        Query(description="Dirección de la ordenación ('asc' o 'desc')", pattern="^(asc|desc)$"),
    ] = "desc",
) -> RespuestaListaUsuarios:
    """Devuelve la lista paginada y filtrada de usuarios."""
    return await servicio.listar_usuarios(
        pagina=pagina,
        por_pagina=por_pagina,
        q=q,
        esta_activo=esta_activo,
        ordenar_por=ordenar_por,
        orden=orden,
    )


@router.get(
    "/{usuario_id}",
    response_model=RespuestaUsuario,
    status_code=status.HTTP_200_OK,
    summary="Obtener usuario por ID",
    description="Recupera la información detallada de un usuario por su identificador UUID.",
    responses={
        200: {"description": "Usuario encontrado"},
        404: {"description": "Usuario no encontrado"},
        422: {"description": "Formato de UUID inválido"},
    },
)
async def obtener_usuario(
    usuario_id: Annotated[uuid.UUID, Path(description="UUID único del usuario")],
    servicio: Annotated[ServicioUsuario, Depends(obtener_servicio_usuario)],
) -> RespuestaUsuario:
    """Busca y retorna un usuario por su ID."""
    return await servicio.obtener_usuario(usuario_id)


@router.patch(
    "/{usuario_id}",
    response_model=RespuestaUsuario,
    status_code=status.HTTP_200_OK,
    summary="Actualizar usuario parcialmente",
    description=(
        "Actualiza los datos de un usuario existente. Solo los campos incluidos "
        "en la petición serán modificados."
    ),
    responses={
        200: {"description": "Usuario actualizado exitosamente"},
        403: {"description": "Prohibido: solo puedes modificar tu propia cuenta"},
        404: {"description": "Usuario no encontrado"},
        409: {"description": "Conflicto: El nuevo email ya está en uso"},
        422: {"description": "Error de validación en los campos enviados"},
    },
)
async def actualizar_usuario(
    usuario_id: Annotated[uuid.UUID, Path(description="UUID único del usuario")],
    datos: ActualizarUsuario,
    servicio: Annotated[ServicioUsuario, Depends(obtener_servicio_usuario)],
    usuario_actual: Annotated[RespuestaUsuario, Depends(obtener_usuario_actual)],
) -> RespuestaUsuario:
    """Actualiza parcialmente los datos de un usuario (solo la propia cuenta)."""
    _verificar_propiedad(usuario_id=usuario_id, usuario_actual=usuario_actual)
    return await servicio.actualizar_usuario(usuario_id=usuario_id, datos=datos)


@router.delete(
    "/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar usuario (soft delete)",
    description=(
        "Realiza un borrado lógico del usuario: establece eliminado_en al timestamp "
        "actual. El registro no se borra físicamente y puede recuperarse con el "
        "endpoint /restaurar. Requiere autenticación JWT."
    ),
    responses={
        204: {"description": "Usuario marcado como eliminado exitosamente"},
        401: {"description": "No autorizado"},
        403: {"description": "Prohibido: solo puedes eliminar tu propia cuenta"},
        404: {"description": "Usuario no encontrado"},
        422: {"description": "Formato de UUID inválido"},
    },
)
async def eliminar_usuario(
    usuario_id: Annotated[uuid.UUID, Path(description="UUID único del usuario")],
    servicio: Annotated[ServicioUsuario, Depends(obtener_servicio_usuario)],
    usuario_actual: Annotated[RespuestaUsuario, Depends(obtener_usuario_actual)],
) -> None:
    """Realiza el borrado lógico (soft delete) de un usuario (solo la propia cuenta)."""
    _verificar_propiedad(usuario_id=usuario_id, usuario_actual=usuario_actual)
    await servicio.eliminar_usuario(usuario_id)


@router.post(
    "/{usuario_id}/restaurar",
    response_model=RespuestaUsuario,
    status_code=status.HTTP_200_OK,
    summary="Restaurar usuario eliminado",
    description=(
        "Restaura un usuario previamente eliminado con soft delete, "
        "estableciendo eliminado_en a None. Requiere autenticación JWT."
    ),
    responses={
        200: {"description": "Usuario restaurado exitosamente"},
        401: {"description": "No autorizado"},
        403: {"description": "Prohibido: solo puedes restaurar tu propia cuenta"},
        404: {"description": "No existe un usuario eliminado con ese ID"},
        422: {"description": "Formato de UUID inválido"},
    },
)
async def restaurar_usuario(
    usuario_id: Annotated[uuid.UUID, Path(description="UUID del usuario eliminado a restaurar")],
    servicio: Annotated[ServicioUsuario, Depends(obtener_servicio_usuario)],
    usuario_actual: Annotated[RespuestaUsuario, Depends(obtener_usuario_actual)],
) -> RespuestaUsuario:
    """Restaura un usuario marcado con soft delete (solo la propia cuenta)."""
    _verificar_propiedad(usuario_id=usuario_id, usuario_actual=usuario_actual)
    return await servicio.restaurar_usuario(usuario_id)
