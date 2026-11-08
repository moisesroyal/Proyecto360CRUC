"""Módulo M2: estructura académica y M5: períodos, aulas y oferta."""
from __future__ import annotations

from datetime import date, time

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, enum_column
from .enums import EstadoActivo, EstadoGrupo, EstadoPeriodo


class Sede(Base, TimestampMixin):
    __tablename__ = "sede"

    id_sede: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    ciudad: Mapped[str | None] = mapped_column(String(120))
    provincia: Mapped[str | None] = mapped_column(String(120))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    facultades: Mapped[list["Facultad"]] = relationship(back_populates="sede")
    aulas: Mapped[list["Aula"]] = relationship(back_populates="sede")
    grupos: Mapped[list["Grupo"]] = relationship(back_populates="sede")
    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="sede")


class Facultad(Base, TimestampMixin):
    __tablename__ = "facultad"

    id_facultad: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_sede: Mapped[int | None] = mapped_column(ForeignKey("sede.id_sede"))
    nombre: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    sede: Mapped[Sede | None] = relationship(back_populates="facultades")
    escuelas: Mapped[list["Escuela"]] = relationship(back_populates="facultad")


class Escuela(Base, TimestampMixin):
    __tablename__ = "escuela"

    id_escuela: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_facultad: Mapped[int] = mapped_column(ForeignKey("facultad.id_facultad"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    facultad: Mapped[Facultad] = relationship(back_populates="escuelas")
    carreras: Mapped[list["Carrera"]] = relationship(back_populates="escuela")


class Carrera(Base, TimestampMixin):
    __tablename__ = "carrera"

    id_carrera: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_escuela: Mapped[int] = mapped_column(ForeignKey("escuela.id_escuela"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    titulo: Mapped[str | None] = mapped_column(String(160))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    escuela: Mapped[Escuela] = relationship(back_populates="carreras")
    planes: Mapped[list["PlanEstudio"]] = relationship(back_populates="carrera")
    estudiantes: Mapped[list["Estudiante"]] = relationship(back_populates="carrera")


class PlanEstudio(Base, TimestampMixin):
    __tablename__ = "plan_estudio"

    id_plan: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_carrera: Mapped[int] = mapped_column(ForeignKey("carrera.id_carrera"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    creditos_totales: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estado: Mapped[EstadoActivo] = mapped_column(
        enum_column(EstadoActivo), default=EstadoActivo.ACTIVO, nullable=False
    )

    carrera: Mapped[Carrera] = relationship(back_populates="planes")
    materias: Mapped[list["PlanMateria"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )
    estudiantes: Mapped[list["Estudiante"]] = relationship(back_populates="plan")


class Materia(Base, TimestampMixin):
    __tablename__ = "materia"

    id_materia: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(180), nullable=False)
    creditos: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    horas_teoricas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    horas_practicas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    planes: Mapped[list["PlanMateria"]] = relationship(
        back_populates="materia", cascade="all, delete-orphan"
    )
    prerequisitos: Mapped[list["Prerrequisito"]] = relationship(
        back_populates="materia",
        foreign_keys="Prerrequisito.id_materia",
        cascade="all, delete-orphan",
    )
    grupos: Mapped[list["Grupo"]] = relationship(back_populates="materia")


class PlanMateria(Base):
    __tablename__ = "plan_materia"

    id_plan: Mapped[int] = mapped_column(
        ForeignKey("plan_estudio.id_plan", ondelete="CASCADE"), primary_key=True
    )
    id_materia: Mapped[int] = mapped_column(
        ForeignKey("materia.id_materia", ondelete="CASCADE"), primary_key=True
    )
    nivel: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), default="obligatoria", nullable=False)

    plan: Mapped[PlanEstudio] = relationship(back_populates="materias")
    materia: Mapped[Materia] = relationship(back_populates="planes")


class Prerrequisito(Base):
    __tablename__ = "prerrequisito"

    id_materia: Mapped[int] = mapped_column(
        ForeignKey("materia.id_materia", ondelete="CASCADE"), primary_key=True
    )
    id_materia_requisito: Mapped[int] = mapped_column(
        ForeignKey("materia.id_materia", ondelete="CASCADE"), primary_key=True
    )

    materia: Mapped[Materia] = relationship(
        back_populates="prerequisitos", foreign_keys=[id_materia]
    )
    materia_requisito: Mapped[Materia] = relationship(foreign_keys=[id_materia_requisito])


class PeriodoAcademico(Base, TimestampMixin):
    __tablename__ = "periodo_academico"

    id_periodo: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), default="semestre", nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    matricula_abierta: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_creditos: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    estado: Mapped[EstadoPeriodo] = mapped_column(
        enum_column(EstadoPeriodo), default=EstadoPeriodo.PLANIFICADO, nullable=False
    )

    grupos: Mapped[list["Grupo"]] = relationship(back_populates="periodo")
    matriculas: Mapped[list["Matricula"]] = relationship(back_populates="periodo")


class Aula(Base, TimestampMixin):
    __tablename__ = "aula"

    id_aula: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_sede: Mapped[int] = mapped_column(ForeignKey("sede.id_sede"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    capacidad: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), default="aula", nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("id_sede", "nombre", name="uq_aula_sede_nombre"),)

    sede: Mapped[Sede] = relationship(back_populates="aulas")
    horarios: Mapped[list["Horario"]] = relationship(back_populates="aula")


class Grupo(Base, TimestampMixin):
    __tablename__ = "grupo"

    id_grupo: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_materia: Mapped[int] = mapped_column(ForeignKey("materia.id_materia"), nullable=False)
    id_periodo: Mapped[int] = mapped_column(
        ForeignKey("periodo_academico.id_periodo"), nullable=False
    )
    id_profesor: Mapped[int | None] = mapped_column(ForeignKey("profesor.id_profesor"))
    id_sede: Mapped[int] = mapped_column(ForeignKey("sede.id_sede"), nullable=False)
    codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    cupo: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    estado: Mapped[EstadoGrupo] = mapped_column(
        enum_column(EstadoGrupo), default=EstadoGrupo.ABIERTO, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("id_periodo", "codigo", name="uq_grupo_periodo_codigo"),
    )

    materia: Mapped[Materia] = relationship(back_populates="grupos")
    periodo: Mapped[PeriodoAcademico] = relationship(back_populates="grupos")
    profesor: Mapped["Profesor | None"] = relationship(back_populates="grupos")
    sede: Mapped[Sede] = relationship(back_populates="grupos")
    horarios: Mapped[list["Horario"]] = relationship(
        back_populates="grupo", cascade="all, delete-orphan"
    )
    detalles: Mapped[list["DetalleMatricula"]] = relationship(back_populates="grupo")


class Horario(Base, TimestampMixin):
    __tablename__ = "horario"

    id_horario: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_grupo: Mapped[int] = mapped_column(
        ForeignKey("grupo.id_grupo", ondelete="CASCADE"), nullable=False
    )
    id_aula: Mapped[int] = mapped_column(ForeignKey("aula.id_aula"), nullable=False)
    dia_semana: Mapped[str] = mapped_column(String(15), nullable=False)
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)

    grupo: Mapped[Grupo] = relationship(back_populates="horarios")
    aula: Mapped[Aula] = relationship(back_populates="horarios")
