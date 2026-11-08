"""Módulo M1: usuarios, roles, permisos y expedientes de personas."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
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
from .enums import EstadoActivo


class Rol(Base, TimestampMixin):
    __tablename__ = "rol"

    id_rol: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(180))

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="rol")
    permisos: Mapped[list["RolPermiso"]] = relationship(
        back_populates="rol", cascade="all, delete-orphan"
    )


class Permiso(Base, TimestampMixin):
    __tablename__ = "permiso"

    id_permiso: Mapped[int] = mapped_column(Integer, primary_key=True)
    modulo: Mapped[str] = mapped_column(String(60), nullable=False)
    accion: Mapped[str] = mapped_column(String(20), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(180))

    __table_args__ = (UniqueConstraint("modulo", "accion", name="uq_permiso_modulo_accion"),)

    roles: Mapped[list["RolPermiso"]] = relationship(
        back_populates="permiso", cascade="all, delete-orphan"
    )


class RolPermiso(Base):
    __tablename__ = "rol_permiso"

    id_rol: Mapped[int] = mapped_column(
        ForeignKey("rol.id_rol", ondelete="CASCADE"), primary_key=True
    )
    id_permiso: Mapped[int] = mapped_column(
        ForeignKey("permiso.id_permiso", ondelete="CASCADE"), primary_key=True
    )

    rol: Mapped[Rol] = relationship(back_populates="permisos")
    permiso: Mapped[Permiso] = relationship(back_populates="roles")


class Usuario(Base, TimestampMixin):
    __tablename__ = "usuario"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_rol: Mapped[int] = mapped_column(ForeignKey("rol.id_rol"), nullable=False)
    id_sede: Mapped[int | None] = mapped_column(ForeignKey("sede.id_sede"))
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    cedula: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(40))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    rol: Mapped[Rol] = relationship(back_populates="usuarios")
    sede: Mapped["Sede | None"] = relationship(back_populates="usuarios")
    estudiante: Mapped["Estudiante | None"] = relationship(
        back_populates="usuario", uselist=False
    )
    profesor: Mapped["Profesor | None"] = relationship(
        back_populates="usuario", uselist=False
    )
    documentos: Mapped[list["Documento"]] = relationship(back_populates="usuario")
    auditorias: Mapped[list["Auditoria"]] = relationship(back_populates="usuario")


class Estudiante(Base, TimestampMixin):
    __tablename__ = "estudiante"

    id_estudiante: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id_usuario"), nullable=False, unique=True
    )
    id_carrera: Mapped[int] = mapped_column(ForeignKey("carrera.id_carrera"), nullable=False)
    id_plan: Mapped[int | None] = mapped_column(ForeignKey("plan_estudio.id_plan"))
    codigo: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    estado: Mapped[EstadoActivo] = mapped_column(
        enum_column(EstadoActivo), default=EstadoActivo.ACTIVO, nullable=False
    )
    indice_academico: Mapped[float] = mapped_column(Numeric(3, 2), default=0, nullable=False)
    anio_ingreso: Mapped[int] = mapped_column(Integer, default=2022, nullable=False)

    usuario: Mapped[Usuario] = relationship(back_populates="estudiante")
    carrera: Mapped["Carrera"] = relationship(back_populates="estudiantes")
    plan: Mapped["PlanEstudio | None"] = relationship(back_populates="estudiantes")
    matriculas: Mapped[list["Matricula"]] = relationship(back_populates="estudiante")


class Profesor(Base, TimestampMixin):
    __tablename__ = "profesor"

    id_profesor: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuario.id_usuario"), nullable=False, unique=True
    )
    id_sede: Mapped[int | None] = mapped_column(ForeignKey("sede.id_sede"))
    categoria: Mapped[str] = mapped_column(String(40), default="docente", nullable=False)
    dedicacion: Mapped[str] = mapped_column(String(40), default="tiempo completo", nullable=False)
    estado: Mapped[EstadoActivo] = mapped_column(
        enum_column(EstadoActivo), default=EstadoActivo.ACTIVO, nullable=False
    )

    usuario: Mapped[Usuario] = relationship(back_populates="profesor")
    titulos: Mapped[list["TituloAcademico"]] = relationship(back_populates="profesor")
    grupos: Mapped[list["Grupo"]] = relationship(back_populates="profesor")


class TituloAcademico(Base, TimestampMixin):
    __tablename__ = "titulo_academico"

    id_titulo: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_profesor: Mapped[int] = mapped_column(
        ForeignKey("profesor.id_profesor", ondelete="CASCADE"), nullable=False
    )
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    institucion: Mapped[str | None] = mapped_column(String(160))
    anio: Mapped[int | None] = mapped_column(Integer)

    profesor: Mapped[Profesor] = relationship(back_populates="titulos")


class Documento(Base, TimestampMixin):
    __tablename__ = "documento"

    id_documento: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(60), nullable=False)
    nombre: Mapped[str] = mapped_column(String(180), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(20), default="cargado", nullable=False)

    usuario: Mapped[Usuario] = relationship(back_populates="documentos")
