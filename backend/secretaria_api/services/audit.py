"""Bitácora de auditoría centralizada."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import Auditoria, EventoLog, Usuario


def registrar_auditoria(
    db: Session,
    usuario: Usuario | None,
    accion: str,
    entidad: str,
    entidad_id: str | int | None = None,
    detalle: str | None = None,
    ip: str | None = None,
) -> Auditoria:
    registro = Auditoria(
        id_usuario=usuario.id_usuario if usuario else None,
        accion=accion.upper(),
        entidad=entidad,
        entidad_id=str(entidad_id) if entidad_id is not None else None,
        detalle=detalle,
        ip=ip,
    )
    db.add(registro)
    return registro


def registrar_evento(
    db: Session, mensaje: str, nivel: str = "INFO", origen: str = "sistema"
) -> EventoLog:
    evento = EventoLog(nivel=nivel.upper(), origen=origen, mensaje=mensaje)
    db.add(evento)
    return evento
