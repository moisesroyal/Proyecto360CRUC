from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EnrollRequest(BaseModel):
    periodo_id: int
    grupos: list[int] = Field(min_length=1)


class EnrollResponse(BaseModel):
    id_matricula: int
    estado: str
    total_creditos: int
    mensaje: str
    advertencias: list[str] = Field(default_factory=list)


class DetalleOut(ORMModel):
    id_detalle: int
    id_matricula: int
    id_grupo: int
    estado: str
    nota_final: float | None = None


class MatriculaOut(ORMModel):
    id_matricula: int
    id_estudiante: int
    id_periodo: int
    fecha: date
    estado: str
    total_creditos: int


class CalificacionCreate(BaseModel):
    id_detalle: int
    evaluacion: str
    nota: float = Field(ge=0, le=100)
    ponderacion: float = Field(default=100, gt=0, le=100)
    observacion: str | None = None


class CalificacionOut(ORMModel):
    id_calificacion: int
    id_detalle: int
    evaluacion: str
    nota: float
    ponderacion: float
    fecha: date
    registrado_por: int | None = None
    observacion: str | None = None


class PagoCreate(BaseModel):
    id_matricula: int
    monto: float = Field(gt=0)
    metodo: str = "transferencia"
    referencia: str | None = None
    estado: str = "pagado"


class PagoOut(ORMModel):
    id_pago: int
    id_matricula: int
    monto: float
    fecha: date
    estado: str
    referencia: str | None = None
    metodo: str
    registrado_por: int | None = None
