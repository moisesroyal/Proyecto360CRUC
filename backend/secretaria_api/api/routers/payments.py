from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...core.database import get_db
from ...models import Estudiante, Matricula, Pago, Usuario
from ...schemas.enrollment import PagoCreate
from ...services.audit import registrar_auditoria, registrar_evento
from ...services.enrollment_service import obtener_estudiante
from ..deps import get_client_ip, get_current_user, require_admin
from ..serializers import group_out

router = APIRouter(prefix="/payments", tags=["Pagos"])


class PagoEstadoUpdate(BaseModel):
    estado: str


def _pago_out(pago: Pago) -> dict:
    return {
        "id_pago": pago.id_pago,
        "id_matricula": pago.id_matricula,
        "monto": float(pago.monto),
        "fecha": pago.fecha,
        "estado": pago.estado,
        "referencia": pago.referencia,
        "metodo": pago.metodo,
        "registrado_por": pago.registrado_por,
        "estudiante": pago.matricula.estudiante.usuario.nombre if pago.matricula and pago.matricula.estudiante else None,
        "codigo_estudiante": pago.matricula.estudiante.codigo if pago.matricula and pago.matricula.estudiante else None,
        "periodo": pago.matricula.periodo.nombre if pago.matricula and pago.matricula.periodo else None,
    }


def _query():
    return select(Pago).options(
        selectinload(Pago.matricula).selectinload(Matricula.estudiante).selectinload(Estudiante.usuario),
        selectinload(Pago.matricula).selectinload(Matricula.periodo),
    )


@router.get("")
def listar_pagos(
    estado: str | None = Query(default=None),
    _: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    consulta = _query()
    if estado:
        consulta = consulta.where(Pago.estado == estado)
    pagos = db.scalars(consulta.order_by(Pago.created_at.desc())).all()
    return [_pago_out(pago) for pago in pagos]


@router.get("/me")
def mis_pagos(
    usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)
):
    estudiante = obtener_estudiante(db, usuario)
    pagos = db.scalars(
        _query()
        .join(Matricula, Matricula.id_matricula == Pago.id_matricula)
        .where(Matricula.id_estudiante == estudiante.id_estudiante)
        .order_by(Pago.created_at.desc())
    ).all()
    return [_pago_out(pago) for pago in pagos]


@router.post("", status_code=status.HTTP_201_CREATED)
def registrar_pago(
    payload: PagoCreate,
    request: Request,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    matricula = db.scalar(
        select(Matricula)
        .where(Matricula.id_matricula == payload.id_matricula)
        .options(selectinload(Matricula.estudiante))
    )
    if not matricula:
        raise HTTPException(status_code=404, detail="Matrícula no encontrada.")
    if matricula.estado == "anulada":
        raise HTTPException(status_code=400, detail="No se puede pagar una matrícula anulada.")

    es_staff = usuario.rol.nombre in {"admin", "admin_facultad", "coordinador", "secretaria"}
    if not es_staff:
        estudiante = obtener_estudiante(db, usuario)
        if matricula.id_estudiante != estudiante.id_estudiante:
            raise HTTPException(status_code=403, detail="No puede registrar pagos de otra matrícula.")

    pago = None
    accion = "CREAR"
    if payload.estado == "pagado":
        pago = db.scalar(
            select(Pago)
            .where(Pago.id_matricula == matricula.id_matricula, Pago.estado == "pendiente")
            .order_by(Pago.created_at.desc(), Pago.id_pago.desc())
            .limit(1)
        )
        if pago:
            accion = "ACTUALIZAR"

    if pago:
        pago.monto = payload.monto
        pago.metodo = payload.metodo
        if payload.referencia:
            pago.referencia = payload.referencia
        pago.estado = "pagado"
        pago.registrado_por = usuario.id_usuario
    else:
        pago = Pago(
            id_matricula=matricula.id_matricula,
            monto=payload.monto,
            metodo=payload.metodo,
            referencia=payload.referencia,
            estado=payload.estado,
            registrado_por=usuario.id_usuario,
        )
        db.add(pago)

    if payload.estado == "pagado":
        matricula.estado = "confirmada"
    db.flush()
    registrar_auditoria(
        db,
        usuario,
        accion,
        "pago",
        pago.id_pago,
        f"Pago {payload.monto} ({payload.estado}) para matrícula {matricula.id_matricula}",
        get_client_ip(request),
    )
    registrar_evento(
        db,
        f"Pago registrado para matrícula {matricula.id_matricula}: ${payload.monto:.2f}",
        origen="pagos",
    )
    db.commit()
    return _pago_out(pago)


@router.patch("/{id_pago}/estado")
def cambiar_estado_pago(
    id_pago: int,
    payload: PagoEstadoUpdate,
    request: Request,
    usuario: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if payload.estado not in {"pendiente", "pagado", "anulado"}:
        raise HTTPException(status_code=400, detail="Estado de pago inválido.")
    pago = db.scalar(_query().where(Pago.id_pago == id_pago))
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado.")
    pago.estado = payload.estado
    if payload.estado == "pagado":
        pago.matricula.estado = "confirmada"
    registrar_auditoria(
        db,
        usuario,
        "ACTUALIZAR",
        "pago",
        pago.id_pago,
        f"Estado cambiado a {payload.estado}",
        get_client_ip(request),
    )
    db.commit()
    return _pago_out(pago)
