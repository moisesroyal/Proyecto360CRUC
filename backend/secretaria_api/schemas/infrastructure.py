from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..models.enums import EstadoNodo, EstadoTransaccion


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class NodoOut(ORMModel):
    id_nodo: int
    nombre: str
    rol: str
    host: str
    estado: EstadoNodo
    latencia_ms: int
    replicacion_pct: float
    id_sede: int | None = None
    ultima_sincronizacion: datetime | None = None


class NodoUpdate(BaseModel):
    estado: EstadoNodo | None = None
    latencia_ms: int | None = None
    replicacion_pct: float | None = None


class TransaccionOut(ORMModel):
    id_transaccion: int
    codigo: str
    tipo: str
    estado: EstadoTransaccion
    nodos_involucrados: int
    detalle: str | None = None
    iniciada_en: datetime
    finalizada_en: datetime | None = None


class SimulateTransactionRequest(BaseModel):
    tipo: str = "Actualización"
    nodos: int = Field(default=3, ge=1, le=10)
    forzar_rollback: bool = False


class AuditoriaOut(ORMModel):
    id_auditoria: int
    id_usuario: int | None = None
    accion: str
    entidad: str
    entidad_id: str | None = None
    detalle: str | None = None
    ip: str | None = None
    fecha: datetime


class EventoLogOut(ORMModel):
    id_evento: int
    nivel: str
    origen: str
    mensaje: str
    fecha: datetime


class QueryRequest(BaseModel):
    sql: str = Field(min_length=6, max_length=5000)


class QueryResponse(BaseModel):
    columnas: list[str]
    filas: list[dict]
    total: int
    mensaje: str


class ReplicationLink(BaseModel):
    origen: str
    destino: str
    latencia_ms: int
    estado: str
