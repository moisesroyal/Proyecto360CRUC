"""Enumeraciones de dominio para los campos de estado.

Se almacenan en PostgreSQL como VARCHAR (native_enum=False) con sus valores
literales ("pendiente", "inscrito", ...) para no requerir migración del esquema
existente; la validación se hace del lado de Python/SQLAlchemy.
"""
from __future__ import annotations

from enum import Enum


def enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class EstadoMatricula(str, Enum):
    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    ANULADA = "anulada"


class EstadoDetalle(str, Enum):
    INSCRITO = "inscrito"
    RETIRADO = "retirado"


class EstadoPago(str, Enum):
    PENDIENTE = "pendiente"
    PAGADO = "pagado"
    ANULADO = "anulado"


class EstadoGrupo(str, Enum):
    ABIERTO = "abierto"
    CERRADO = "cerrado"


class EstadoPeriodo(str, Enum):
    PLANIFICADO = "planificado"
    ABIERTO = "abierto"
    CERRADO = "cerrado"


class EstadoActivo(str, Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"


class EstadoNodo(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class EstadoTransaccion(str, Enum):
    PREPARE = "PREPARE"
    COMMIT = "COMMIT"
    ROLLBACK = "ROLLBACK"
    EJECUTANDO = "EJECUTANDO"
