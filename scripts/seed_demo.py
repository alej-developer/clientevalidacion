"""
Seed de datos ficticios para la demo pública (portafolio).

Crea usuarios claramente ficticios (emails @ejemplo.com) para que la
demo desplegada tenga contenido sin exponer datos reales. Idempotente:
los emails ya registrados se omiten.

Uso:
    python -m scripts.seed_demo

Todos los usuarios demo comparten la contraseña documentada en el README
para que quien revise el portafolio pueda iniciar sesión.
"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import fabrica_sesiones
from app.modelos.usuario import Usuario
from app.repositorios.usuario import RepositorioUsuario
from app.servicios.usuario import ServicioUsuario

CONTRASENA_DEMO = "Demo#2026!"

USUARIOS_DEMO: list[tuple[str, str]] = [
    ("Lucía Fernández", "lucia.fernandez@ejemplo.com"),
    ("Marcos Aguilar", "marcos.aguilar@ejemplo.com"),
    ("Elena Rivas", "elena.rivas@ejemplo.com"),
    ("Diego Serrano", "diego.serrano@ejemplo.com"),
    ("Carmen Ortiz", "carmen.ortiz@ejemplo.com"),
    ("Pablo Navarro", "pablo.navarro@ejemplo.com"),
    ("Sofía Delgado", "sofia.delgado@ejemplo.com"),
    ("Andrés Molina", "andres.molina@ejemplo.com"),
    ("Valeria Campos", "valeria.campos@ejemplo.com"),
    ("Javier Roldán", "javier.roldan@ejemplo.com"),
]


async def sembrar_usuarios_demo(sesion: AsyncSession) -> tuple[int, int]:
    """
    Inserta los usuarios demo omitiendo los emails ya registrados.

    Args:
        sesion: Sesión asíncrona de base de datos.

    Retorna:
        Tupla (creados, ya_existentes).
    """
    repositorio = RepositorioUsuario(sesion=sesion)
    creados = 0
    existentes = 0
    for nombre, email in USUARIOS_DEMO:
        if await repositorio.existe_email(email):
            existentes += 1
            continue
        sesion.add(
            Usuario(
                nombre=nombre,
                email=email,
                contrasena_hash=ServicioUsuario._generar_hash_contrasena(CONTRASENA_DEMO),
                esta_activo=True,
            )
        )
        creados += 1
    await sesion.flush()
    return creados, existentes


async def main() -> None:
    """Ejecuta el seed contra la base de datos configurada y hace commit."""
    async with fabrica_sesiones() as sesion:
        creados, existentes = await sembrar_usuarios_demo(sesion)
        await sesion.commit()
        print(f"Seed demo: {creados} usuarios creados, {existentes} ya existían.")


if __name__ == "__main__":
    asyncio.run(main())
