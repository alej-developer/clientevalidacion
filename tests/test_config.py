"""Pruebas de la configuración: JWT_SECRETO es obligatorio y no tiene valor por defecto."""

import pytest
from pydantic import ValidationError

from app.core.config import Configuracion

SECRETO_VALIDO = "secreto-de-prueba-distinto-al-de-la-suite"


def test_jwt_secreto_obligatorio_si_falta(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sin JWT_SECRETO la configuración es inválida y la aplicación no arranca."""
    monkeypatch.delenv("JWT_SECRETO", raising=False)

    with pytest.raises(ValidationError):
        Configuracion(_env_file=None)


def test_jwt_secreto_vacio_es_invalido(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un JWT_SECRETO vacío equivale a no tener secreto."""
    monkeypatch.setenv("JWT_SECRETO", "   ")

    with pytest.raises(ValidationError):
        Configuracion(_env_file=None)


def test_jwt_secreto_definido_es_valido(monkeypatch: pytest.MonkeyPatch) -> None:
    """Con JWT_SECRETO definido la configuración carga ese valor."""
    monkeypatch.setenv("JWT_SECRETO", SECRETO_VALIDO)

    config = Configuracion(_env_file=None)

    assert config.jwt_secreto == SECRETO_VALIDO
