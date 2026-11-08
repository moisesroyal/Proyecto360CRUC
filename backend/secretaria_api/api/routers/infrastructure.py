from __future__ import annotations

import re
from datetime import date, datetime, time, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models import (
    Auditoria,
    Base,
    EstadoDetalle,
    EstadoNodo,
    EstadoTransaccion,
    EventoLog,
    Nodo,
    TransaccionDistribuida,
    Usuario,
)
from ...schemas.infrastructure import QueryRequest, SimulateTransactionRequest
from ...services.audit import registrar_auditoria, registrar_evento
from ..deps import get_client_ip, get_current_user, require_admin
from ..serializers import node_out, transaction_out

router = APIRouter(prefix="/infrastructure", tags=["Infraestructura distribuida"])

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|vacuum|"
    r"reindex|comment|merge|call|execute|do|set|reset|show|listen|notify)\b",
    re.IGNORECASE,
)


def _serialize(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


@router.get("/nodes")
def listar_nodos(_: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    nodos = db.scalars(select(Nodo).order_by(Nodo.id_nodo)).all()
    return [node_out(nodo) for nodo in nodos]


@router.post("/nodes/{id_nodo}/toggle")
def alternar_nodo(
    id_nodo: int,
    request: Request,
    usuario: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    nodo = db.get(Nodo, id_nodo)
    if not nodo:
        raise HTTPException(status_code=404, detail="Nodo no encontrado.")
    nodo.estado = EstadoNodo.OFFLINE if nodo.estado == EstadoNodo.ONLINE else EstadoNodo.ONLINE
    nodo.replicacion_pct = 0 if nodo.estado == EstadoNodo.OFFLINE else 100
    nodo.ultima_sincronizacion = datetime.now(timezone.utc)
    registrar_auditoria(
        db,
        usuario,
        "ACTUALIZAR",
        "nodo",
        nodo.id_nodo,
        f"Nodo {nodo.nombre} -> {nodo.estado.value}",
        get_client_ip(request),
    )
    registrar_evento(
        db,
        f"Nodo {nodo.nombre} cambiado a estado {nodo.estado.value}.",
        nivel="WARNING" if nodo.estado == EstadoNodo.OFFLINE else "INFO",
        origen="infraestructura",
    )
    db.commit()
    return node_out(nodo)


@router.get("/replication")
def replicacion(_: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    nodos = db.scalars(select(Nodo).order_by(Nodo.id_nodo)).all()
    enlaces = []
    for i, origen in enumerate(nodos):
        for destino in nodos[i + 1 :]:
            enlaces.append(
                {
                    "origen": origen.nombre,
                    "destino": destino.nombre,
                    "latencia_ms": max(origen.latencia_ms, destino.latencia_ms),
                    "estado": "Conectado"
                    if origen.estado == EstadoNodo.ONLINE and destino.estado == EstadoNodo.ONLINE
                    else "Degradado",
                }
            )
    return {
        "nodos": [node_out(nodo) for nodo in nodos],
        "enlaces": enlaces,
        "replicacion_activa": all(nodo.estado == EstadoNodo.ONLINE for nodo in nodos) if nodos else False,
        "simulado": True,
        "nota": "Replicación lógica simulada: los enlaces y estados se calculan sobre una única base de datos; no existe sincronización real entre nodos.",
    }


@router.get("/transactions")
def transacciones(
    limit: int = Query(default=25, ge=1, le=200),
    _: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    registros = db.scalars(
        select(TransaccionDistribuida)
        .order_by(TransaccionDistribuida.iniciada_en.desc())
        .limit(limit)
    ).all()
    return [transaction_out(tx) for tx in registros]


@router.post("/transactions/simulate")
def simular_transaccion(
    payload: SimulateTransactionRequest,
    request: Request,
    usuario: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total = int(db.scalar(select(func.count()).select_from(TransaccionDistribuida)) or 0) + 1
    estado_final = EstadoTransaccion.ROLLBACK if payload.forzar_rollback else EstadoTransaccion.COMMIT
    transaccion = TransaccionDistribuida(
        codigo=f"TXN-{1000 + total}",
        tipo=payload.tipo,
        estado=estado_final,
        nodos_involucrados=payload.nodos,
        detalle=f"Simulación 2PC: PREPARE -> {estado_final.value}",
        finalizada_en=datetime.now(timezone.utc),
    )
    db.add(transaccion)
    registrar_auditoria(
        db,
        usuario,
        "SIMULAR",
        "transaccion_distribuida",
        transaccion.codigo,
        f"2PC {estado_final.value} en {payload.nodos} nodos",
        get_client_ip(request),
    )
    registrar_evento(
        db,
        f"Transacción {transaccion.codigo} finalizada en {estado_final.value}.",
        nivel="WARNING" if payload.forzar_rollback else "INFO",
        origen="2pc",
    )
    db.commit()
    return transaction_out(transaccion)


@router.get("/logs")
def logs(
    limit: int = Query(default=50, ge=1, le=500),
    _: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    eventos = db.scalars(
        select(EventoLog).order_by(EventoLog.fecha.desc()).limit(limit)
    ).all()
    return [
        {
            "id_evento": evento.id_evento,
            "nivel": evento.nivel,
            "origen": evento.origen,
            "mensaje": evento.mensaje,
            "fecha": evento.fecha,
        }
        for evento in eventos
    ]


@router.get("/audit")
def auditoria(
    limit: int = Query(default=100, ge=1, le=500),
    _: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    registros = db.scalars(
        select(Auditoria).order_by(Auditoria.fecha.desc()).limit(limit)
    ).all()
    return [
        {
            "id_auditoria": r.id_auditoria,
            "usuario": r.usuario.nombre if r.usuario else "Sistema",
            "accion": r.accion,
            "entidad": r.entidad,
            "entidad_id": r.entidad_id,
            "detalle": r.detalle,
            "ip": r.ip,
            "fecha": r.fecha,
        }
        for r in registros
    ]


@router.post("/query")
def ejecutar_consulta(
    payload: QueryRequest,
    request: Request,
    usuario: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    sql = payload.sql.strip().rstrip(";").strip()
    if not re.match(r"^(select|with)\b", sql, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Solo se permiten consultas SELECT/WITH.")
    if ";" in sql:
        raise HTTPException(status_code=400, detail="No se permiten múltiples sentencias.")
    if _FORBIDDEN.search(sql):
        raise HTTPException(status_code=400, detail="La consulta contiene una operación no permitida.")

    try:
        resultado = db.execute(text(sql))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error SQL: {str(exc).splitlines()[0]}")

    columnas = list(resultado.keys())
    filas = [
        {col: _serialize(valor) for col, valor in zip(columnas, fila)}
        for fila in resultado.fetchmany(100)
    ]
    registrar_auditoria(
        db,
        usuario,
        "CONSULTA",
        "sql",
        None,
        f"Consulta ejecutada: {sql[:180]}",
        get_client_ip(request),
    )
    db.commit()
    return {
        "columnas": columnas,
        "filas": filas,
        "total": len(filas),
        "mensaje": "Consulta ejecutada sobre la base de datos única (simulación de integración de fragmentos). Se muestran hasta 100 filas.",
    }


@router.get("/data-dictionary")
def diccionario(_: Usuario = Depends(get_current_user)):
    tablas = []
    for nombre, tabla in sorted(Base.metadata.tables.items()):
        pk = [col.name for col in tabla.primary_key.columns]
        columnas = []
        for columna in tabla.columns:
            fk = None
            if columna.foreign_keys:
                objetivo = next(iter(columna.foreign_keys))
                fk = f"{objetivo.column.table.name}.{objetivo.column.name}"
            columnas.append(
                {
                    "nombre": columna.name,
                    "tipo": str(columna.type),
                    "nulable": columna.nullable,
                    "pk": columna.name in pk,
                    "fk": fk,
                }
            )
        tablas.append({"tabla": nombre, "pk": pk, "columnas": columnas})
    return tablas


@router.get("/fragmentation")
def fragmentacion(_: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    from ...models import Estudiante, Grupo, Matricula, Sede

    sedes = db.scalars(select(Sede).order_by(Sede.id_sede)).all()
    fragmentos = []
    for sede in sedes:
        estudiantes = int(
            db.scalar(
                select(func.count())
                .select_from(Estudiante)
                .join(Usuario, Usuario.id_usuario == Estudiante.id_usuario)
                .where(Usuario.id_sede == sede.id_sede)
            )
            or 0
        )
        grupos = int(
            db.scalar(select(func.count()).select_from(Grupo).where(Grupo.id_sede == sede.id_sede))
            or 0
        )
        fragmentos.append(
            {
                "sede": sede.nombre,
                "id_sede": sede.id_sede,
                "fragmento": f"estudiante_sede_{sede.id_sede}",
                "estudiantes": estudiantes,
                "grupos": grupos,
                "estrategia": "Horizontal primaria por sede",
            }
        )
    return {
        "fragmentos": fragmentos,
        "replicas": ["Panamá replica catálogo institucional", "Coclé y Veraguas replican matrícula"],
        "estrategias": [
            {
                "tipo": "Horizontal",
                "descripcion": "Estudiantes y matrículas particionados por sede regional.",
            },
            {
                "tipo": "Vertical",
                "descripcion": "Catálogo académico separado de datos de matrícula y calificaciones.",
            },
            {
                "tipo": "Híbrida",
                "descripcion": "Catálogo replicado en Panamá; matrícula fragmentada por sede.",
            },
        ],
        "simulado": True,
        "nota": "Fragmentación horizontal simulada: los fragmentos se calculan por sede sobre una única base de datos; no hay particiones físicas.",
    }


@router.get("/concurrency")
def simular_concurrencia(
    _: Usuario = Depends(require_admin), db: Session = Depends(get_db)
):
    from ...models import DetalleMatricula

    bloqueos = int(
        db.scalar(
            select(func.count())
            .select_from(DetalleMatricula)
            .where(DetalleMatricula.estado == EstadoDetalle.INSCRITO)
        )
        or 0
    )
    return {
        "pasos": [
            "Inicio de transacción distribuida",
            "Bloqueo compartido sobre el grupo seleccionado",
            "Validación de cupo y prerrequisitos",
            "Escritura en detalle de matrícula",
            "COMMIT / liberación de bloqueos",
        ],
        "registros_bloqueados": bloqueos,
        "simulado": True,
        "mensaje": "Simulación lógica de bloqueo de dos fases completada sin interbloqueos. Los bloqueos reales de matrícula usan SELECT ... FOR UPDATE en la base de datos única.",
    }
