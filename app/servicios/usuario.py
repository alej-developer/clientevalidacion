"""
Servicio de negocio para la entidad Usuario.

Contiene toda la lógica de negocio desacoplada de la capa web:
validaciones complejas, reglas de negocio, hash de contraseñas
y orquestación de llamadas al repositorio.
"""

import hashlib
import secrets
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.excepciones.excepciones import (
    ConflictoError,
    NoEncontradoError,
    ValidacionError,
)
from app.core.logging import obtener_logger
from app.esquemas.usuario import (
    ActualizarUsuario,
    CrearUsuario,
    RespuestaListaUsuarios,
    RespuestaUsuario,
)
from app.modelos.usuario import Usuario
from app.repositorios.usuario import RepositorioUsuario

_logger = obtener_logger("servicio.usuario")


class ServicioUsuario:
    """
    Servicio de lógica de negocio para la gestión de usuarios.

    Encapsula las reglas de negocio, validaciones complejas y
    orquesta las interacciones con el repositorio de datos.
    Completamente desacoplado de la capa HTTP.

    Args:
        sesion: Sesión asíncrona de base de datos inyectada por dependencia.
    """

    def __init__(self, sesion: AsyncSession) -> None:
        self._repositorio = RepositorioUsuario(sesion=sesion)
        self._sesion = sesion

    # --- Hash de contraseñas ---

    @staticmethod
    def _generar_hash_contrasena(contrasena: str) -> str:
        """
        Genera un hash seguro de la contraseña usando PBKDF2-SHA256.

        Utiliza un salt aleatorio de 32 bytes y 600.000 iteraciones
        siguiendo las recomendaciones de OWASP para almacenamiento
        seguro de contraseñas.

        Args:
            contrasena: Contraseña en texto plano.

        Retorna:
            Hash de la contraseña en formato 'salt:hash' codificado en hexadecimal.
        """
        salt = secrets.token_hex(32)
        hash_derivado = hashlib.pbkdf2_hmac(
            "sha256",
            contrasena.encode("utf-8"),
            salt.encode("utf-8"),
            iterations=600_000,
        )
        return f"{salt}:{hash_derivado.hex()}"

    @staticmethod
    def _verificar_contrasena(contrasena: str, hash_almacenado: str) -> bool:
        """
        Verifica una contraseña contra su hash almacenado.

        Args:
            contrasena: Contraseña en texto plano a verificar.
            hash_almacenado: Hash almacenado en formato 'salt:hash'.

        Retorna:
            True si la contraseña coincide, False en caso contrario.
        """
        try:
            salt, hash_original = hash_almacenado.split(":")
        except ValueError:
            return False
        hash_verificacion = hashlib.pbkdf2_hmac(
            "sha256",
            contrasena.encode("utf-8"),
            salt.encode("utf-8"),
            iterations=600_000,
        )
        return secrets.compare_digest(hash_verificacion.hex(), hash_original)

    # --- Operaciones de negocio ---

    async def crear_usuario(self, datos: CrearUsuario) -> RespuestaUsuario:
        """
        Crea un nuevo usuario aplicando todas las reglas de negocio.

        Reglas:
        - El email no debe estar registrado previamente.
        - La contraseña se almacena como hash seguro PBKDF2.
        - El nombre se normaliza (espacios extra eliminados).

        Args:
            datos: Esquema de creación con los datos validados por Pydantic.

        Retorna:
            Esquema de respuesta con el usuario recién creado.

        Raises:
            ConflictoError: Si el email ya está registrado.
        """
        # Verificar unicidad del email
        if await self._repositorio.existe_email(datos.email):
            raise ConflictoError(
                mensaje=f"El email '{datos.email}' ya está registrado.",
                detalles={"campo": "email", "valor": datos.email},
            )

        # Preparar datos para la creación
        datos_creacion = {
            "nombre": datos.nombre,
            "email": datos.email,
            "contrasena_hash": self._generar_hash_contrasena(datos.contrasena),
            "esta_activo": True,
        }

        usuario = await self._repositorio.crear(datos_creacion)
        _logger.info("Usuario creado exitosamente: %s (ID: %s)", usuario.email, usuario.id)

        return RespuestaUsuario.model_validate(usuario)

    async def obtener_usuario(self, usuario_id: uuid.UUID) -> RespuestaUsuario:
        """
        Obtiene un usuario por su identificador UUID.

        Args:
            usuario_id: UUID del usuario a buscar.

        Retorna:
            Esquema de respuesta con los datos del usuario.

        Raises:
            NoEncontradoError: Si el usuario no existe.
        """
        usuario = await self._repositorio.obtener_por_id(usuario_id)
        if usuario is None:
            raise NoEncontradoError(
                mensaje=f"No se encontró un usuario con ID '{usuario_id}'.",
                detalles={"campo": "id", "valor": str(usuario_id)},
            )
        return RespuestaUsuario.model_validate(usuario)

    async def obtener_usuario_por_email(self, email: str) -> RespuestaUsuario:
        """
        Obtiene un usuario por su dirección de correo electrónico.

        Args:
            email: Email del usuario a buscar.

        Retorna:
            Esquema de respuesta con los datos del usuario.

        Raises:
            NoEncontradoError: Si no existe un usuario con ese email.
        """
        usuario = await self._repositorio.obtener_por_email(email)
        if usuario is None:
            raise NoEncontradoError(
                mensaje=f"No se encontró un usuario con email '{email}'.",
                detalles={"campo": "email", "valor": email},
            )
        return RespuestaUsuario.model_validate(usuario)

    async def listar_usuarios(
        self,
        pagina: int = 1,
        por_pagina: int = 20,
        solo_activos: bool = False,
    ) -> RespuestaListaUsuarios:
        """
        Lista usuarios con paginación.

        Args:
            pagina: Número de página (mínimo 1).
            por_pagina: Elementos por página (máximo 100).
            solo_activos: Si es True, filtra solo usuarios con cuentas activas.

        Retorna:
            Esquema de respuesta con la lista paginada de usuarios.

        Raises:
            ValidacionError: Si los parámetros de paginación son inválidos.
        """
        if pagina < 1:
            raise ValidacionError(
                mensaje="El número de página debe ser mayor o igual a 1.",
                detalles={"campo": "pagina", "valor": pagina},
            )
        if por_pagina < 1 or por_pagina > 100:
            raise ValidacionError(
                mensaje="El número de elementos por página debe estar entre 1 y 100.",
                detalles={"campo": "por_pagina", "valor": por_pagina},
            )

        if solo_activos:
            usuarios, total = await self._repositorio.listar_activos(
                pagina=pagina,
                por_pagina=por_pagina,
            )
        else:
            usuarios, total = await self._repositorio.listar_paginado(
                pagina=pagina,
                por_pagina=por_pagina,
            )

        return RespuestaListaUsuarios(
            elementos=[RespuestaUsuario.model_validate(u) for u in usuarios],
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
        )

    async def actualizar_usuario(
        self,
        usuario_id: uuid.UUID,
        datos: ActualizarUsuario,
    ) -> RespuestaUsuario:
        """
        Actualiza un usuario existente con los datos proporcionados.

        Reglas:
        - Solo actualiza los campos no nulos del esquema.
        - Si se cambia el email, verifica que no esté en uso.
        - Si se cambia la contraseña, genera un nuevo hash.

        Args:
            usuario_id: UUID del usuario a actualizar.
            datos: Esquema de actualización parcial.

        Retorna:
            Esquema de respuesta con el usuario actualizado.

        Raises:
            NoEncontradoError: Si el usuario no existe.
            ConflictoError: Si el nuevo email ya está en uso por otro usuario.
        """
        usuario = await self._repositorio.obtener_por_id(usuario_id)
        if usuario is None:
            raise NoEncontradoError(
                mensaje=f"No se encontró un usuario con ID '{usuario_id}'.",
                detalles={"campo": "id", "valor": str(usuario_id)},
            )

        # Verificar unicidad del nuevo email si se está cambiando
        if (
            datos.email is not None
            and datos.email != usuario.email
            and await self._repositorio.existe_email(datos.email)
        ):
            raise ConflictoError(
                mensaje=f"El email '{datos.email}' ya está en uso por otro usuario.",
                detalles={"campo": "email", "valor": datos.email},
            )

        # Preparar datos para la actualización
        datos_actualizacion: dict[str, str | bool | None] = {}

        if datos.nombre is not None:
            datos_actualizacion["nombre"] = datos.nombre
        if datos.email is not None:
            datos_actualizacion["email"] = datos.email
        if datos.esta_activo is not None:
            datos_actualizacion["esta_activo"] = datos.esta_activo
        if datos.contrasena is not None:
            datos_actualizacion["contrasena_hash"] = self._generar_hash_contrasena(
                datos.contrasena
            )

        if not datos_actualizacion:
            _logger.debug("Actualización sin cambios para usuario ID %s", usuario_id)
            return RespuestaUsuario.model_validate(usuario)

        usuario_actualizado = await self._repositorio.actualizar(usuario, datos_actualizacion)
        _logger.info("Usuario actualizado: %s (ID: %s)", usuario_actualizado.email, usuario_id)

        return RespuestaUsuario.model_validate(usuario_actualizado)

    async def eliminar_usuario(self, usuario_id: uuid.UUID) -> None:
        """
        Realiza un borrado lógico (soft delete) del usuario.

        El usuario no se elimina físicamente de la base de datos:
        se establece eliminado_en al timestamp actual. El registro
        queda oculto en todas las consultas normales pero puede
        ser restaurado con restaurar_usuario().

        Args:
            usuario_id: UUID del usuario a eliminar.

        Raises:
            NoEncontradoError: Si el usuario no existe o ya está eliminado.
        """
        usuario = await self._repositorio.obtener_por_id(usuario_id)
        if usuario is None:
            raise NoEncontradoError(
                mensaje=f"No se encontró un usuario con ID '{usuario_id}'.",
                detalles={"campo": "id", "valor": str(usuario_id)},
            )

        await self._repositorio.eliminar(usuario)
        _logger.info("Usuario eliminado (soft): %s (ID: %s)", usuario.email, usuario_id)

    async def restaurar_usuario(self, usuario_id: uuid.UUID) -> RespuestaUsuario:
        """
        Restaura un usuario previamente eliminado lógicamente.

        Establece eliminado_en a None, haciendo al usuario visible
        de nuevo en todas las consultas normales.

        Args:
            usuario_id: UUID del usuario a restaurar.

        Retorna:
            Esquema de respuesta con el usuario restaurado.

        Raises:
            NoEncontradoError: Si no existe ningún usuario eliminado con ese ID.
        """
        usuario = await self._repositorio.obtener_eliminado_por_id(usuario_id)
        if usuario is None:
            raise NoEncontradoError(
                mensaje=f"No se encontró un usuario eliminado con ID '{usuario_id}'.",
                detalles={"campo": "id", "valor": str(usuario_id)},
            )

        usuario_restaurado = await self._repositorio.restaurar(usuario)
        _logger.info(
            "Usuario restaurado: %s (ID: %s)", usuario_restaurado.email, usuario_id
        )
        return RespuestaUsuario.model_validate(usuario_restaurado)

    async def verificar_credenciales(self, email: str, contrasena: str) -> Usuario:
        """
        Verifica las credenciales de un usuario para autenticación.

        Args:
            email: Email del usuario.
            contrasena: Contraseña en texto plano.

        Retorna:
            La instancia del modelo Usuario si las credenciales son válidas.

        Raises:
            NoEncontradoError: Si el usuario no existe.
            ValidacionError: Si la contraseña es incorrecta o la cuenta está desactivada.
        """
        usuario = await self._repositorio.obtener_por_email(email)
        if usuario is None:
            raise NoEncontradoError(
                mensaje="Credenciales inválidas.",
                detalles={"campo": "email"},
            )

        if not usuario.esta_activo:
            raise ValidacionError(
                mensaje="La cuenta del usuario está desactivada.",
                detalles={"campo": "esta_activo", "valor": False},
            )

        if not self._verificar_contrasena(contrasena, usuario.contrasena_hash):
            raise ValidacionError(
                mensaje="Credenciales inválidas.",
                detalles={"campo": "contrasena"},
            )

        _logger.info("Credenciales verificadas para usuario: %s", email)
        return usuario
