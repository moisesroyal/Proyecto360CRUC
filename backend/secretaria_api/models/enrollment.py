"""Módulo M3: matrícula, detalle, calificaciones y pagos."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, enum_column
from .enums import EstadoDetalle, EstadoMatricula, EstadoPago


class Matricula(Base, TimestampMixin):
    __tablename__ = "matricula"

    id_matricula: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_estudiante: Mapped[int] = mapped_column(
        ForeignKey("estudiante.id_estudiante"), nullable=False
    )
    id_periodo: Mapped[int] = mapped_column(
        ForeignKey("periodo_academico.id_periodo"), nullable=False
    )
    fecha: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    estado: Mapped[EstadoMatricula] = mapped_column(
        enum_column(EstadoMatricula), default=EstadoMatricula.PENDIENTE, nullable=False
    )
    total_creditos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("id_estudiante", "id_periodo", name="uq_matricula_estudiante_periodo"),
    )

    estudiante: Mapped["Estudiante"] = relationship(back_populates="matriculas")
    periodo: Mapped["PeriodoAcademico"] = relationship(back_populates="matriculas")
    detalles: Mapped[list["DetalleMatricula"]] = relationship(
        back_populates="matricula", cascade="all, delete-orphan"
    )
    pagos: Mapped[list["Pago"]] = relationship(back_populates="matricula")


class DetalleMatricula(Base, TimestampMixin):
    __tablename__ = "detalle_matricula"

    id_detalle: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_matricula: Mapped[int] = mapped_column(
        ForeignKey("matricula.id_matricula", ondelete="CASCADE"), nullable=False
    )
    id_grupo: Mapped[int] = mapped_column(ForeignKey("grupo.id_grupo"), nullable=False)
    estado: Mapped[EstadoDetalle] = mapped_column(
        enum_column(EstadoDetalle), default=EstadoDetalle.INSCRITO, nullable=False
    )
    nota_final: Mapped[float | None] = mapped_column(Numeric(5, 2))

    __table_args__ = (
        UniqueConstraint("id_matricula", "id_grupo", name="uq_detalle_matricula_grupo"),
    )

    matricula: Mapped[Matricula] = relationship(back_populates="detalles")
    grupo: Mapped["Grupo"] = relationship(back_populates="detalles")
    calificaciones: Mapped[list["Calificacion"]] = relationship(
        back_populates="detalle", cascade="all, delete-orphan"
    )


class Calificacion(Base, TimestampMixin):
    __tablename__ = "calificacion"

    id_calificacion: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_detalle: Mapped[int] = mapped_column(
        ForeignKey("detalle_matricula.id_detalle", ondelete="CASCADE"), nullable=False
    )
    evaluacion: Mapped[str] = mapped_column(String(80), nullable=False)
    nota: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    ponderacion: Mapped[float] = mapped_column(Numeric(5, 2), default=100, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    registrado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id_usuario"))
    observacion: Mapped[str | None] = mapped_column(Text)

    detalle: Mapped[DetalleMatricula] = relationship(back_populates="calificaciones")


class Pago(Base, TimestampMixin):
    __tablename__ = "pago"

    id_pago: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_matricula: Mapped[int] = mapped_column(
        ForeignKey("matricula.id_matricula"), nullable=False
    )
    monto: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    estado: Mapped[EstadoPago] = mapped_column(
        enum_column(EstadoPago), default=EstadoPago.PENDIENTE, nullable=False
    )
    referencia: Mapped[str | None] = mapped_column(String(80))
    metodo: Mapped[str] = mapped_column(String(40), default="transferencia", nullable=False)
    registrado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id_usuario"))

    matricula: Mapped[Matricula] = relationship(back_populates="pagos")
