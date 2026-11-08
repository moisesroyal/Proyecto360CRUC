from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...core.database import get_db
from ...models import (
    Calificacion,
    DetalleMatricula,
    Estudiante,
    EstadoDetalle,
    Grupo,
    Matricula,
    Profesor,
    Usuario,
)
from ...schemas.enrollment import CalificacionCreate
from ...services.audit import registrar_auditoria, registrar_evento
from ..deps import get_client_ip, get_current_user, require_roles, require_staff
from ..serializers import group_out

router = APIRouter(prefix="/grades", tags=["Calificaciones"])


def _detalle_query():
    return select(DetalleMatricula).options(
        selectinload(DetalleMatricula.matricula).selectinload(Matricula.estudiante).selectinload(Estudiante.usuario),
        selectinload(DetalleMatricula.grupo).selectinload(Grupo.materia),
        selectinload(DetalleMatricula.grupo).selectinload(Grupo.profesor).selectinload(Profesor.usuario),
        selectinload(DetalleMatricula.grupo).selectinload(Grupo.periodo),
        selectinload(DetalleMatricula.grupo).selectinload(Grupo.sede),
        selectinload(DetalleMatricula.grupo).selectinload(Grupo.horarios),
        selectinload(DetalleMatricula.calificaciones),
    )


def _recalcular_detalle(db: Session, detalle: DetalleMatricula) -> None:
    total_peso = sum(float(c.ponderacion) for c in detalle.calificaciones)
    if total_peso > 0:
        promedio = sum(float(c.nota) * float(c.ponderacion) for c in detalle.calificaciones) / total_peso
        detalle.nota_final = round(promedio, 2)
    else:
        detalle.nota_final = None

    matricula = detalle.matricula
    estudiante = matricula.estudiante
    notas = [
        (float(d.nota_final), d.grupo.materia.creditos)
        for d in db.scalars(
            select(DetalleMatricula)
            .join(Matricula, Matricula.id_matricula == DetalleMatricula.id_matricula)
            .where(
                Matricula.id_estudiante == estudiante.id_estudiante,
                DetalleMatricula.nota_final.is_not(None),
            )
            .options(selectinload(DetalleMatricula.grupo).selectinload(Grupo.materia))
        ).all()
    ]
    if detalle not in db.scalars(
        select(DetalleMatricula).where(DetalleMatricula.id_detalle == detalle.id_detalle)
    ).all():
        notas.append(
            (float(detalle.nota_final or 0), detalle.grupo.materia.creditos)
        )
    if notas:
        peso = sum(creditos for _, creditos in notas) or 1
        promedio = sum(nota * creditos for nota, creditos in notas) / peso
        estudiante.indice_academico = round((promedio / 100) * 3, 2)


@router.get("/detalles")
def listar_detalles(
    periodo_id: int | None = Query(default=None),
    grupo_id: int | None = Query(default=None),
    _: Usuario = Depends(require_staff),
    db: Session = Depends(get_db),
):
    consulta = _detalle_query().join(Matricula, Matricula.id_matricula == DetalleMatricula.id_matricula)
    if periodo_id:
        consulta = consulta.where(Matricula.id_periodo == periodo_id)
    if grupo_id:
        consulta = consulta.where(DetalleMatricula.id_grupo == grupo_id)
    detalles = db.scalars(consulta.order_by(DetalleMatricula.id_detalle.desc())).unique().all()
    return [
        {
            "id_detalle": detalle.id_detalle,
            "id_matricula": detalle.id_matricula,
            "estado": detalle.estado,
            "nota_final": float(detalle.nota_final) if detalle.nota_final is not None else None,
            "estudiante": detalle.matricula.estudiante.usuario.nombre,
            "codigo_estudiante": detalle.matricula.estudiante.codigo,
            "grupo": group_out(db, detalle.grupo),
            "calificaciones": [
                {
                    "id_calificacion": c.id_calificacion,
                    "evaluacion": c.evaluacion,
                    "nota": float(c.nota),
                    "ponderacion": float(c.ponderacion),
                    "fecha": c.fecha,
                }
                for c in detalle.calificaciones
            ],
        }
        for detalle in detalles
    ]


@router.get("")
def listar_calificaciones(
    id_detalle: int | None = Query(default=None),
    _: Usuario = Depends(require_staff),
    db: Session = Depends(get_db),
):
    consulta = select(Calificacion).options(
        selectinload(Calificacion.detalle).selectinload(DetalleMatricula.grupo).selectinload(Grupo.materia),
        selectinload(Calificacion.detalle).selectinload(DetalleMatricula.matricula).selectinload(Matricula.estudiante).selectinload(Estudiante.usuario),
    )
    if id_detalle:
        consulta = consulta.where(Calificacion.id_detalle == id_detalle)
    calificaciones = db.scalars(consulta.order_by(Calificacion.fecha.desc())).all()
    return [
        {
            "id_calificacion": c.id_calificacion,
            "id_detalle": c.id_detalle,
            "estudiante": c.detalle.matricula.estudiante.usuario.nombre,
            "materia": c.detalle.grupo.materia.nombre,
            "codigo": c.detalle.grupo.materia.codigo,
            "evaluacion": c.evaluacion,
            "nota": float(c.nota),
            "ponderacion": float(c.ponderacion),
            "fecha": c.fecha,
            "observacion": c.observacion,
        }
        for c in calificaciones
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def registrar_calificacion(
    payload: CalificacionCreate,
    request: Request,
    usuario: Usuario = Depends(require_staff),
    db: Session = Depends(get_db),
):
    detalle = db.scalar(_detalle_query().where(DetalleMatricula.id_detalle == payload.id_detalle))
    if not detalle:
        raise HTTPException(status_code=404, detail="Detalle de matrícula no encontrado.")
    if detalle.estado != EstadoDetalle.INSCRITO:
        raise HTTPException(status_code=400, detail="La asignatura no está activa.")

    if usuario.rol.nombre == "profesor":
        profesor = db.scalar(select(Profesor).where(Profesor.id_usuario == usuario.id_usuario))
        if not profesor or detalle.grupo.id_profesor != profesor.id_profesor:
            raise HTTPException(status_code=403, detail="Solo puede calificar sus propios grupos.")

    calificacion = Calificacion(
        id_detalle=detalle.id_detalle,
        evaluacion=payload.evaluacion,
        nota=payload.nota,
        ponderacion=payload.ponderacion,
        observacion=payload.observacion,
        registrado_por=usuario.id_usuario,
    )
    db.add(calificacion)
    db.flush()
    detalle.calificaciones.append(calificacion)
    _recalcular_detalle(db, detalle)

    registrar_auditoria(
        db,
        usuario,
        "CREAR",
        "calificacion",
        calificacion.id_calificacion,
        f"{payload.evaluacion}={payload.nota} para detalle {detalle.id_detalle}",
        get_client_ip(request),
    )
    registrar_evento(
        db,
        f"Calificación registrada: {detalle.grupo.materia.codigo} - {usuario.nombre}",
        origen="calificaciones",
    )
    db.commit()
    return {
        "id_calificacion": calificacion.id_calificacion,
        "nota_final": float(detalle.nota_final) if detalle.nota_final is not None else None,
    }


@router.delete("/{id_calificacion}")
def eliminar_calificacion(
    id_calificacion: int,
    request: Request,
    usuario: Usuario = Depends(require_roles("admin", "secretaria")),
    db: Session = Depends(get_db),
):
    calificacion = db.scalar(
        select(Calificacion)
        .where(Calificacion.id_calificacion == id_calificacion)
        .options(selectinload(Calificacion.detalle).selectinload(DetalleMatricula.calificaciones))
    )
    if not calificacion:
        raise HTTPException(status_code=404, detail="Calificación no encontrada.")
    detalle = calificacion.detalle
    db.delete(calificacion)
    db.flush()
    detalle.calificaciones = [c for c in detalle.calificaciones if c.id_calificacion != id_calificacion]
    _recalcular_detalle(db, detalle)
    registrar_auditoria(
        db,
        usuario,
        "ELIMINAR",
        "calificacion",
        id_calificacion,
        "Calificación eliminada",
        get_client_ip(request),
    )
    db.commit()
    return {"ok": True}
