"""
Esquemas Pydantic v2 para la entidad Usuario.

Define los DTOs de entrada/salida con validaciones estrictas:
- UsuarioBase: Campos compartidos entre esquemas.
- CrearUsuario: Esquema de creación con validaciones de campo.
- ActualizarUsuario: Esquema de actualización parcial.
- RespuestaUsuario: Esquema de respuesta con serialización ORM.
"""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _validar_complejidad_contrasena(valor: str) -> str:
    """
    Verifica los requisitos de complejidad de una contraseña.

    Requisitos: al menos una mayúscula, una minúscula, un dígito
    y un carácter especial. Compartida por CrearUsuario y ActualizarUsuario.
    """
    if not re.search(r"[A-Z]", valor):
        raise ValueError("La contraseña debe contener al menos una letra mayúscula.")
    if not re.search(r"[a-z]", valor):
        raise ValueError("La contraseña debe contener al menos una letra minúscula.")
    if not re.search(r"\d", valor):
        raise ValueError("La contraseña debe contener al menos un dígito.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\;'/~`]", valor):
        raise ValueError("La contraseña debe contener al menos un carácter especial.")
    return valor


class UsuarioBase(BaseModel):
    """Campos compartidos entre todos los esquemas de Usuario."""

    nombre: str = Field(
        min_length=2,
        max_length=150,
        description="Nombre completo del usuario",
        examples=["Juan García López"],
    )
    email: EmailStr = Field(
        max_length=255,
        description="Dirección de correo electrónico",
        examples=["juan.garcia@ejemplo.com"],
    )


class CrearUsuario(UsuarioBase):
    """
    Esquema para la creación de un nuevo usuario.

    Incluye validaciones estrictas de formato de email y
    requisitos de complejidad de contraseña.
    """

    contrasena: str = Field(
        min_length=8,
        max_length=128,
        description="Contraseña del usuario (mínimo 8 caracteres)",
        examples=["MiContrasena#Segura123"],
    )

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, valor: str) -> str:
        """Normaliza el email (minúsculas, sin espacios). El formato lo valida EmailStr."""
        return valor.lower().strip()

    @field_validator("contrasena")
    @classmethod
    def validar_complejidad_contrasena(cls, valor: str) -> str:
        """
        Valida que la contraseña cumpla los requisitos de complejidad.

        Requisitos definidos en _validar_complejidad_contrasena.
        """
        return _validar_complejidad_contrasena(valor)

    @field_validator("nombre")
    @classmethod
    def limpiar_nombre(cls, valor: str) -> str:
        """Elimina espacios extra y capitaliza el nombre."""
        return " ".join(valor.split()).strip()


class ActualizarUsuario(BaseModel):
    """
    Esquema para la actualización parcial de un usuario.

    Todos los campos son opcionales. Solo los campos enviados
    serán actualizados en la base de datos.
    """

    nombre: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
        description="Nuevo nombre completo del usuario",
    )
    email: EmailStr | None = Field(
        default=None,
        max_length=255,
        description="Nueva dirección de correo electrónico",
    )
    contrasena: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="Nueva contraseña del usuario",
    )
    esta_activo: bool | None = Field(
        default=None,
        description="Estado de activación de la cuenta",
    )

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, valor: str | None) -> str | None:
        """Normaliza el email si se proporciona. El formato lo valida EmailStr."""
        if valor is None:
            return valor
        return valor.lower().strip()

    @field_validator("contrasena")
    @classmethod
    def validar_complejidad_contrasena(cls, valor: str | None) -> str | None:
        """Valida la complejidad de la contraseña si se proporciona."""
        if valor is None:
            return valor
        return _validar_complejidad_contrasena(valor)

    @field_validator("nombre")
    @classmethod
    def limpiar_nombre(cls, valor: str | None) -> str | None:
        """Limpia el nombre si se proporciona."""
        if valor is None:
            return valor
        return " ".join(valor.split()).strip()


class RespuestaUsuario(BaseModel):
    """
    Esquema de respuesta para la entidad Usuario.

    Serializa automáticamente desde el modelo ORM gracias
    a la configuración `from_attributes`.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Identificador único del usuario")
    nombre: str = Field(description="Nombre completo del usuario")
    email: str = Field(description="Dirección de correo electrónico")
    esta_activo: bool = Field(description="Indica si la cuenta está activa")
    creado_en: datetime = Field(description="Fecha de creación del registro")
    actualizado_en: datetime = Field(description="Fecha de última actualización")
    eliminado_en: datetime | None = Field(
        default=None,
        description="Fecha de borrado lógico. None indica que el usuario está activo.",
    )


class RespuestaListaUsuarios(BaseModel):
    """Esquema de respuesta paginada para listados de usuarios."""

    elementos: list[RespuestaUsuario] = Field(description="Lista de usuarios")
    total: int = Field(description="Número total de registros")
    pagina: int = Field(description="Página actual")
    por_pagina: int = Field(description="Elementos por página")


class RespuestaUsuarioPublica(BaseModel):
    """
    Vista pública de un usuario (API abierta de portafolio).

    NO incluye email ni marcas de borrado: la API es pública a propósito
    y los listados no exponen datos de contacto. El email solo lo ve
    el propio usuario autenticado (GET /auth/yo o su propio detalle).
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Identificador único del usuario")
    nombre: str = Field(description="Nombre completo del usuario")
    esta_activo: bool = Field(description="Indica si la cuenta está activa")
    creado_en: datetime = Field(description="Fecha de creación del registro")


class RespuestaListaUsuariosPublica(BaseModel):
    """Esquema de respuesta paginada para el listado público (sin emails)."""

    elementos: list[RespuestaUsuarioPublica] = Field(description="Lista de usuarios")
    total: int = Field(description="Número total de registros")
    pagina: int = Field(description="Página actual")
    por_pagina: int = Field(description="Elementos por página")
