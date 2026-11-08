from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...core.database import get_db
from ...models import (
    Calificacion,
    DetalleMatricula,
    Estudiante,
    Grupo,
    Horario,
    Matricula,
    PeriodoAcademico,
    Profesor,
    Usuario,
)
from ...schemas.enrollment import EnrollRequest
from ...services.audit import registrar_auditoria, registrar_evento
from ...services.enrollment_service import EnrollmentError, matricular, obtener_estudiante
from ..deps import get_client_ip, get_current_user, require_admin
from ..serializers import group_out

router = APIRouter(prefix="/enrollments", tags=["Matrícula"])


def _matricula_query():
    return select(Matricula).options(
        selectinload(Matricula.estudiante).selectinload(Estudiante.usuario),
        selectinload(Matricula.estudiante).selectinload(Estudiante.carrera),
        selectinload(Matricula.periodo),
        selectinload(Matricula.pagos),
        selectinload(Matricula.detalles).selectinload(DetalleMatricula.grupo).selectinload(Grupo.materia),
        selectinload(Matricula.detalles).selectinload(DetalleMatricula.grupo).selectinload(Grupo.profesor).selectinload(Profesor.usuario),
        selectinload(Matricula.detalles).selectinload(DetalleMatricula.grupo).selectinload(Grupo.sede),
        selectinload(Matricula.detalles).selectinload(DetalleMatricula.grupo).selectinload(Grupo.periodo),
        selectinload(Matricula.detalles).selectinload(DetalleMatricula.grupo).selectinload(Grupo.horarios).selectinload(Horario.aula),
        selectinload(Matricula.detalles).selectinload(DetalleMatricula.calificaciones),
    )


def _matricula_out(db: Session, matricula: Matricula) -> dict:
    return {
        "id_matricula": matricula.id_matricula,
        "estado": matricula.estado,
        "fecha": matricula.fecha,
        "total_creditos": matricula.total_creditos,
        "id_estudiante": matricula.id_estudiante,
        "estudiante": matricula.estudiante.usuario.nombre if matricula.estudiante else None,
        "codigo": matricula.estudiante.codigo if matricula.estudiante else None,
        "carrera": matricula.estudiante.carrera.nombre if matricula.estudiante else None,
        "periodo": {
            "id_periodo": matricula.periodo.id_periodo,
            "nombre": matricula.periodo.nombre,
        }
        if matricula.periodo
        else None,
        "detalles": [
            {
                "id_detalle": detalle.id_detalle,
                "estado": detalle.estado,
                "nota_final": float(detalle.nota_final) if detalle.nota_final is not None else None,
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
            for detalle in matricula.detalles
        ],
        "pagos": [
            {
                "id_pago": pago.id_pago,
                "monto": float(pago.monto),
                "estado": pago.estado,
                "fecha": pago.fecha,
                "metodo": pago.metodo,
                "referencia": pago.referencia,
            }
            for pago in matricula.pagos
        ],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def crear_matricula(
    payload: EnrollRequest,
    request: Request,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        matricula, advertencias = matricular(
            db,
            usuario,
            payload.periodo_id,
            payload.grupos,
            ip=get_client_ip(request),
        )
    except EnrollmentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    matricula = db.scalar(_matricula_query().where(Matricula.id_matricula == matricula.id_matricula))
    return {
        "id_matricula": matricula.id_matricula,
        "estado": matricula.estado,
        "total_creditos": matricula.total_creditos,
        "mensaje": "Matrícula registrada correctamente.",
        "advertencias": advertencias,
        "matricula": _matricula_out(db, matricula),
    }


@router.get("/me")
def mi_matricula(
    usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)
):
    estudiante = obtener_estudiante(db, usuario)
    matriculas = db.scalars(
        _matricula_query()
        .join(PeriodoAcademico, PeriodoAcademico.id_periodo == Matricula.id_periodo)
        .where(Matricula.id_estudiante == estudiante.id_estudiante)
        .order_by(
            PeriodoAcademico.anio.desc(),
            PeriodoAcademico.numero.desc(),
            Matricula.id_matricula.desc(),
        )
    ).unique().all()
    return [_matricula_out(db, matricula) for matricula in matriculas]


@router.get("")
def listar_matriculas(
    periodo_id: int | None = Query(default=None),
    estado: str | None = Query(default=None),
    _: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    consulta = _matricula_query()
    if periodo_id:
        consulta = consulta.where(Matricula.id_periodo == periodo_id)
    if estado:
        consulta = consulta.where(Matricula.estado == estado)
    matriculas = db.scalars(consulta.order_by(Matricula.created_at.desc())).unique().all()
    return [_matricula_out(db, matricula) for matricula in matriculas]


@router.get("/{id_matricula}")
def detalle_matricula(
    id_matricula: int,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    matricula = db.scalar(_matricula_query().where(Matricula.id_matricula == id_matricula))
    if not matricula:
        raise HTTPException(status_code=404, detail="Matrícula no encontrada.")
    if usuario.rol.nombre not in {"admin", "admin_facultad", "coordinador", "secretaria"}:
        estudiante = obtener_estudiante(db, usuario)
        if matricula.id_estudiante != estudiante.id_estudiante:
            raise HTTPException(status_code=403, detail="No puede consultar esta matrícula.")
    return _matricula_out(db, matricula)


@router.post("/{id_matricula}/confirmar")
def confirmar_matricula(
    id_matricula: int,
    request: Request,
    usuario: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    matricula = db.scalar(_matricula_query().where(Matricula.id_matricula == id_matricula))
    if not matricula:
        raise HTTPException(status_code=404, detail="Matrícula no encontrada.")
    if matricula.estado == "anulada":
        raise HTTPException(status_code=400, detail="No se puede confirmar una matrícula anulada.")
    if not matricula.detalles:
        raise HTTPException(status_code=400, detail="La matrícula no tiene asignaturas.")
    matricula.estado = "confirmada"
    for detalle in matricula.detalles:
        detalle.estado = "inscrito"
    registrar_auditoria(
        db,
        usuario,
        "ACTUALIZAR",
        "matricula",
        matricula.id_matricula,
        "Matrícula confirmada por Secretaría",
        get_client_ip(request),
    )
    registrar_evento(db, f"Matrícula {matricula.id_matricula} confirmada.", origen="secretaria")
    db.commit()
    return _matricula_out(db, matricula)


@router.delete("/{id_matricula}")
def anular_matricula(
    id_matricula: int,
    request: Request,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    matricula = db.scalar(_matricula_query().where(Matricula.id_matricula == id_matricula))
    if not matricula:
        raise HTTPException(status_code=404, detail="Matrícula no encontrada.")
    if usuario.rol.nombre not in {"admin", "admin_facultad", "coordinador", "secretaria"}:
        estudiante = obtener_estudiante(db, usuario)
        if matricula.id_estudiante != estudiante.id_estudiante:
            raise HTTPException(status_code=403, detail="No puede anular esta matrícula.")
        if matricula.estado == "confirmada":
            raise HTTPException(
                status_code=400,
                detail="La matrícula ya está confirmada. Contacte a Secretaría para anularla.",
            )
    matricula.estado = "anulada"
    for detalle in matricula.detalles:
        detalle.estado = "retirado"
    matricula.total_creditos = 0
    registrar_auditoria(
        db,
        usuario,
        "ANULAR",
        "matricula",
        matricula.id_matricula,
        "Matrícula anulada",
        get_client_ip(request),
    )
    db.commit()
    return {"ok": True, "id_matricula": id_matricula, "estado": matricula.estado}


@router.delete("/detalles/{id_detalle}")
def retirar_asignatura(
    id_detalle: int,
    request: Request,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    detalle = db.scalar(
        select(DetalleMatricula)
        .where(DetalleMatricula.id_detalle == id_detalle)
        .options(
            selectinload(DetalleMatricula.matricula),
            selectinload(DetalleMatricula.grupo).selectinload(Grupo.materia),
        )
    )
    if not detalle:
        raise HTTPException(status_code=404, detail="Detalle de matrícula no encontrado.")
    if detalle.estado != "inscrito":
        raise HTTPException(status_code=400, detail="La asignatura ya no está inscrita.")

    es_staff = usuario.rol.nombre in {"admin", "admin_facultad", "coordinador", "secretaria"}
    if not es_staff:
        estudiante = obtener_estudiante(db, usuario)
        if detalle.matricula.id_estudiante != estudiante.id_estudiante:
            raise HTTPException(status_code=403, detail="No puede retirar esta asignatura.")
        if detalle.matricula.estado == "confirmada":
            raise HTTPException(
                status_code=400,
                detail="La matrícula está confirmada. Contacte a Secretaría para retiros.",
            )

    detalle.estado = "retirado"
    matricula = detalle.matricula
    matricula.total_creditos = sum(
        d.grupo.materia.creditos for d in matricula.detalles if d.estado == "inscrito"
    )
    registrar_auditoria(
        db,
        usuario,
        "RETIRAR",
        "detalle_matricula",
        detalle.id_detalle,
        f"Retiro de {detalle.grupo.codigo}",
        get_client_ip(request),
    )
    db.commit()
    return {"ok": True, "id_detalle": id_detalle, "total_creditos": matricula.total_creditos}


@router.get("/me/calificaciones")
def mis_calificaciones(
    usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)
):
    estudiante = obtener_estudiante(db, usuario)
    calificaciones = db.scalars(
        select(Calificacion)
        .join(DetalleMatricula, DetalleMatricula.id_detalle == Calificacion.id_detalle)
        .join(Matricula, Matricula.id_matricula == DetalleMatricula.id_matricula)
        .where(Matricula.id_estudiante == estudiante.id_estudiante)
        .options(selectinload(Calificacion.detalle).selectinload(DetalleMatricula.grupo).selectinload(Grupo.materia))
        .order_by(Calificacion.fecha.desc())
    ).all()
    return [
        {
            "id_calificacion": c.id_calificacion,
            "materia": c.detalle.grupo.materia.nombre,
            "codigo": c.detalle.grupo.materia.codigo,
            "evaluacion": c.evaluacion,
            "nota": float(c.nota),
            "ponderacion": float(c.ponderacion),
            "fecha": c.fecha,
        }
        for c in calificaciones
    ]
