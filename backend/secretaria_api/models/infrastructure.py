"""Infraestructura distribuida, bitácora y monitoreo 2PC."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Nodo(Base, TimestampMixin):
    __tablename__ = "nodo"

    id_nodo: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_sede: Mapped[int | None] = mapped_column(ForeignKey("sede.id_sede"))
    nombre: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    rol: Mapped[str] = mapped_column(String(120), default="nodo regional", nullable=False)
    host: Mapped[str] = mapped_column(String(120), default="localhost", nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="online", nullable=False)
    latencia_ms: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    replicacion_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=100, nullable=False)
    ultima_sincronizacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TransaccionDistribuida(Base, TimestampMixin):
    __tablename__ = "transaccion_distribuida"

    id_transaccion: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="PREPARE", nullable=False)
    nodos_involucrados: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    detalle: Mapped[str | None] = mapped_column(Text)
    iniciada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finalizada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Auditoria(Base, TimestampMixin):
    __tablename__ = "auditoria"

    id_auditoria: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_usuario: Mapped[int | None] = mapped_column(ForeignKey("usuario.id_usuario"))
    accion: Mapped[str] = mapped_column(String(40), nullable=False)
    entidad: Mapped[str] = mapped_column(String(80), nullable=False)
    entidad_id: Mapped[str | None] = mapped_column(String(80))
    detalle: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str | None] = mapped_column(String(60))
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    usuario: Mapped["Usuario | None"] = relationship(back_populates="auditorias")


class EventoLog(Base, TimestampMixin):
    __tablename__ = "evento_log"

    id_evento: Mapped[int] = mapped_column(Integer, primary_key=True)
    nivel: Mapped[str] = mapped_column(String(20), default="INFO", nullable=False)
    origen: Mapped[str] = mapped_column(String(80), default="sistema", nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
