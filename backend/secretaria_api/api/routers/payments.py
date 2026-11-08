from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...core.config import settings
from ...core.database import get_db
from ...models import (
    Estudiante,
    EstadoMatricula,
    Matricula,
    Pago,
    Usuario,
)
from ...schemas.enrollment import EstadoPago, PagoCreate
from ...services.audit import registrar_auditoria, registrar_evento
from ..deps import (
    estudiante_actual,
    get_client_ip,
    get_current_user,
    require_admin,
)
from ..serializers import group_out

router = APIRouter(prefix="/payments", tags=["Pagos"])


class PagoEstadoUpdate(BaseModel):
    estado: EstadoPago


def _tarifa_esperada(db: Session, matricula: Matricula) -> float:
    """Monto esperado: el de la boleta pendiente si existe; si no, la tarifa configurada."""
    pendiente = db.scalar(
        select(Pago)
        .where(Pago.id_matricula == matricula.id_matricula, Pago.estado == EstadoPago.PENDIENTE)
        .order_by(Pago.created_at.desc(), Pago.id_pago.desc())
        .limit(1)
    )
    if pendiente:
        return float(pendiente.monto)
    return settings.matricula_fee


def _validar_monto(monto: float, tarifa: float) -> None:
    if abs(monto - tarifa) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"El monto ({monto:.2f}) no coincide con la tarifa esperada ({tarifa:.2f}).",
        )


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
        try:
            estado_enum = EstadoPago(estado)
        except ValueError:
            raise HTTPException(status_code=400, detail="Estado de pago inválido.")
        consulta = consulta.where(Pago.estado == estado_enum)
    pagos = db.scalars(consulta.order_by(Pago.created_at.desc())).all()
    return [_pago_out(pago) for pago in pagos]


@router.get("/me")
def mis_pagos(
    usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)
):
    estudiante = estudiante_actual(db, usuario)
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
    if matricula.estado == EstadoMatricula.ANULADA:
        raise HTTPException(status_code=400, detail="No se puede pagar una matrícula anulada.")

    es_staff = usuario.rol.nombre in {"admin", "admin_facultad", "coordinador", "secretaria"}
    if not es_staff:
        estudiante = estudiante_actual(db, usuario)
        if matricula.id_estudiante != estudiante.id_estudiante:
            raise HTTPException(status_code=403, detail="No puede registrar pagos de otra matrícula.")

    tarifa = _tarifa_esperada(db, matricula)
    _validar_monto(payload.monto, tarifa)

    pago = None
    accion = "CREAR"
    if payload.estado == EstadoPago.PAGADO:
        pago = db.scalar(
            select(Pago)
            .where(Pago.id_matricula == matricula.id_matricula, Pago.estado == EstadoPago.PENDIENTE)
            .order_by(Pago.created_at.desc(), Pago.id_pago.desc())
            .limit(1)
        )
        if pago:
            accion = "ACTUALIZAR"

    if pago:
        pago.monto = tarifa
        pago.metodo = payload.metodo
        if payload.referencia:
            pago.referencia = payload.referencia
        pago.estado = EstadoPago.PAGADO
        pago.registrado_por = usuario.id_usuario
    else:
        pago = Pago(
            id_matricula=matricula.id_matricula,
            monto=tarifa,
            metodo=payload.metodo,
            referencia=payload.referencia,
            estado=payload.estado,
            registrado_por=usuario.id_usuario,
        )
        db.add(pago)

    if payload.estado == EstadoPago.PAGADO:
        matricula.estado = EstadoMatricula.CONFIRMADA
    db.flush()
    registrar_auditoria(
        db,
        usuario,
        accion,
        "pago",
        pago.id_pago,
        f"Pago {tarifa:.2f} ({payload.estado.value}) para matrícula {matricula.id_matricula}",
        get_client_ip(request),
    )
    registrar_evento(
        db,
        f"Pago registrado para matrícula {matricula.id_matricula}: ${tarifa:.2f}",
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
    pago = db.scalar(_query().where(Pago.id_pago == id_pago))
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado.")
    estado_anterior = pago.estado
    pago.estado = payload.estado
    if payload.estado == EstadoPago.PAGADO:
        pago.matricula.estado = EstadoMatricula.CONFIRMADA
    elif estado_anterior == EstadoPago.PAGADO and pago.matricula.estado == EstadoMatricula.CONFIRMADA:
        pago.matricula.estado = EstadoMatricula.PENDIENTE
    registrar_auditoria(
        db,
        usuario,
        "ACTUALIZAR",
        "pago",
        pago.id_pago,
        f"Estado cambiado de {estado_anterior.value} a {payload.estado.value}",
        get_client_ip(request),
    )
    db.commit()
    return _pago_out(pago)
