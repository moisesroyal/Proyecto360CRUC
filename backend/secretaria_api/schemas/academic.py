from __future__ import annotations

from datetime import date, time

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SedeCreate(BaseModel):
    nombre: str
    ciudad: str | None = None
    provincia: str | None = None


class SedeOut(ORMModel):
    id_sede: int
    nombre: str
    ciudad: str | None = None
    provincia: str | None = None
    activo: bool


class FacultadCreate(BaseModel):
    nombre: str
    codigo: str
    id_sede: int | None = None
    descripcion: str | None = None


class FacultadOut(ORMModel):
    id_facultad: int
    nombre: str
    codigo: str
    id_sede: int | None = None
    activo: bool


class EscuelaCreate(BaseModel):
    nombre: str
    codigo: str
    id_facultad: int


class EscuelaOut(ORMModel):
    id_escuela: int
    nombre: str
    codigo: str
    id_facultad: int
    activo: bool


class CarreraCreate(BaseModel):
    nombre: str
    codigo: str
    id_escuela: int
    titulo: str | None = None


class CarreraOut(ORMModel):
    id_carrera: int
    nombre: str
    codigo: str
    id_escuela: int
    titulo: str | None = None
    activo: bool


class PlanCreate(BaseModel):
    nombre: str
    anio: int
    id_carrera: int
    creditos_totales: int = 0


class PlanOut(ORMModel):
    id_plan: int
    nombre: str
    anio: int
    id_carrera: int
    creditos_totales: int
    estado: str


class MateriaCreate(BaseModel):
    codigo: str
    nombre: str
    creditos: int = Field(default=3, ge=1, le=12)
    horas_teoricas: int = 0
    horas_practicas: int = 0
    descripcion: str | None = None


class MateriaOut(ORMModel):
    id_materia: int
    codigo: str
    nombre: str
    creditos: int
    horas_teoricas: int
    horas_practicas: int
    descripcion: str | None = None
    activo: bool


class PlanMateriaCreate(BaseModel):
    id_plan: int
    id_materia: int
    nivel: int = 1
    tipo: str = "obligatoria"


class PrerrequisitoCreate(BaseModel):
    id_materia: int
    id_materia_requisito: int


class PeriodoCreate(BaseModel):
    nombre: str
    anio: int
    numero: int
    tipo: str = "semestre"
    fecha_inicio: date
    fecha_fin: date
    estado: str = "planificado"
    matricula_abierta: bool = False
    max_creditos: int = 24


class PeriodoOut(ORMModel):
    id_periodo: int
    nombre: str
    anio: int
    numero: int
    tipo: str
    fecha_inicio: date
    fecha_fin: date
    estado: str
    matricula_abierta: bool
    max_creditos: int


class AulaCreate(BaseModel):
    nombre: str
    id_sede: int
    capacidad: int = 30
    tipo: str = "aula"


class AulaOut(ORMModel):
    id_aula: int
    nombre: str
    id_sede: int
    capacidad: int
    tipo: str


class HorarioCreate(BaseModel):
    id_aula: int
    dia_semana: str
    hora_inicio: time
    hora_fin: time


class HorarioOut(ORMModel):
    id_horario: int
    id_grupo: int
    id_aula: int
    dia_semana: str
    hora_inicio: time
    hora_fin: time


class GrupoCreate(BaseModel):
    id_materia: int
    id_periodo: int
    id_sede: int
    id_profesor: int | None = None
    codigo: str
    cupo: int = 30
    horarios: list[HorarioCreate] = Field(default_factory=list)


class GrupoOut(ORMModel):
    id_grupo: int
    id_materia: int
    id_periodo: int
    id_sede: int
    id_profesor: int | None = None
    codigo: str
    cupo: int
    estado: str
