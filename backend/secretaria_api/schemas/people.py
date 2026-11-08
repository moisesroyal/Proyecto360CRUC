from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RolOut(ORMModel):
    id_rol: int
    nombre: str
    descripcion: str | None = None


class PermisoOut(ORMModel):
    id_permiso: int
    modulo: str
    accion: str
    descripcion: str | None = None


class UsuarioCreate(BaseModel):
    nombre: str = Field(min_length=3, max_length=160)
    email: str
    cedula: str
    password: str = Field(min_length=8, max_length=128)
    id_rol: int
    id_sede: int | None = None
    telefono: str | None = None
    id_carrera: int | None = None
    id_plan: int | None = None
    codigo: str | None = None
    anio_ingreso: int | None = None
    categoria: str | None = None
    dedicacion: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value:
            raise ValueError("Correo electrónico inválido")
        return value


class UsuarioOut(ORMModel):
    id_usuario: int
    nombre: str
    email: str
    cedula: str
    telefono: str | None = None
    activo: bool
    id_rol: int
    id_sede: int | None = None
    ultimo_acceso: datetime | None = None


class UsuarioStatusUpdate(BaseModel):
    activo: bool


class EstudianteCreate(BaseModel):
    id_usuario: int
    id_carrera: int
    id_plan: int | None = None
    codigo: str
    anio_ingreso: int = 2022


class EstudianteOut(ORMModel):
    id_estudiante: int
    id_usuario: int
    id_carrera: int
    id_plan: int | None = None
    codigo: str
    estado: str
    indice_academico: float
    anio_ingreso: int


class ProfesorCreate(BaseModel):
    id_usuario: int
    id_sede: int | None = None
    categoria: str = "docente"
    dedicacion: str = "tiempo completo"


class ProfesorOut(ORMModel):
    id_profesor: int
    id_usuario: int
    id_sede: int | None = None
    categoria: str
    dedicacion: str
    estado: str


class TituloCreate(BaseModel):
    titulo: str
    institucion: str | None = None
    anio: int | None = None


class TituloOut(ORMModel):
    id_titulo: int
    id_profesor: int
    titulo: str
    institucion: str | None = None
    anio: int | None = None


class DocumentoCreate(BaseModel):
    id_usuario: int
    tipo: str
    nombre: str
    url: str | None = None


class DocumentoOut(ORMModel):
    id_documento: int
    id_usuario: int
    tipo: str
    nombre: str
    url: str | None = None
    estado: str
