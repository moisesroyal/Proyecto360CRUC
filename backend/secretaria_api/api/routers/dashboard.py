from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ...core.database import get_db
from ...models import (
    Calificacion,
    Carrera,
    DetalleMatricula,
    Estudiante,
    Grupo,
    Horario,
    Materia,
    Matricula,
    Nodo,
    Pago,
    PeriodoAcademico,
    Profesor,
)
from ...services.enrollment_service import cupos_disponibles, obtener_estudiante
from ..deps import get_current_user, require_admin
from ..serializers import group_out, node_out, student_out
from ...models import Usuario

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _periodo_actual(db: Session) -> PeriodoAcademico | None:
    return db.scalar(
        select(PeriodoAcademico)
        .order_by(PeriodoAcademico.matricula_abierta.desc(), PeriodoAcademico.anio.desc(), PeriodoAcademico.numero.desc())
        .limit(1)
    )


@router.get("/summary")
def summary(
    _: Usuario = Depends(require_admin), db: Session = Depends(get_db)
) -> dict:
    def contar(modelo) -> int:
        return int(db.scalar(select(func.count()).select_from(modelo)) or 0)

    nodos = list(db.scalars(select(Nodo).order_by(Nodo.id_nodo)).all())
    periodo = _periodo_actual(db)

    ultimas = db.execute(
        select(Matricula, Estudiante, Usuario, PeriodoAcademico)
        .join(Estudiante, Estudiante.id_estudiante == Matricula.id_estudiante)
        .join(Usuario, Usuario.id_usuario == Estudiante.id_usuario)
        .join(PeriodoAcademico, PeriodoAcademico.id_periodo == Matricula.id_periodo)
        .order_by(Matricula.created_at.desc())
        .limit(6)
    ).all()

    carreras = db.execute(
        select(Carrera.nombre, func.count(Estudiante.id_estudiante))
        .outerjoin(Estudiante, Estudiante.id_carrera == Carrera.id_carrera)
        .group_by(Carrera.id_carrera, Carrera.nombre)
        .order_by(func.count(Estudiante.id_estudiante).desc())
        .limit(6)
    ).all()

    return {
        "kpis": {
            "estudiantes": contar(Estudiante),
            "profesores": contar(Profesor),
            "carreras": contar(Carrera),
            "materias": contar(Materia),
            "grupos": contar(Grupo),
            "matriculas": contar(Matricula),
            "pagos_pendientes": int(
                db.scalar(
                    select(func.count()).select_from(Pago).where(Pago.estado == "pendiente")
                )
                or 0
            ),
            "nodos_online": sum(1 for nodo in nodos if nodo.estado == "online"),
            "nodos_total": len(nodos),
            "latencia_promedio": round(
                sum(nodo.latencia_ms for nodo in nodos) / len(nodos), 1
            )
            if nodos
            else 0,
        },
        "periodo": {
            "id_periodo": periodo.id_periodo,
            "nombre": periodo.nombre,
            "estado": periodo.estado,
            "matricula_abierta": periodo.matricula_abierta,
            "fecha_inicio": periodo.fecha_inicio,
            "fecha_fin": periodo.fecha_fin,
        }
        if periodo
        else None,
        "nodos": [node_out(nodo) for nodo in nodos],
        "matriculas_recientes": [
            {
                "id_matricula": matricula.id_matricula,
                "estudiante": usuario.nombre,
                "codigo": estudiante.codigo,
                "periodo": periodo_academico.nombre,
                "estado": matricula.estado,
                "creditos": matricula.total_creditos,
                "fecha": matricula.fecha,
            }
            for matricula, estudiante, usuario, periodo_academico in ultimas
        ],
        "carreras": [{"carrera": nombre, "estudiantes": total} for nombre, total in carreras],
    }


@router.get("/student")
def student_dashboard(
    usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    estudiante = obtener_estudiante(db, usuario)
    estudiante = db.scalar(
        select(Estudiante)
        .where(Estudiante.id_estudiante == estudiante.id_estudiante)
        .options(
            selectinload(Estudiante.usuario),
            selectinload(Estudiante.carrera),
            selectinload(Estudiante.plan),
        )
    )
    matricula = db.scalar(
        select(Matricula)
        .join(PeriodoAcademico, PeriodoAcademico.id_periodo == Matricula.id_periodo)
        .where(Matricula.id_estudiante == estudiante.id_estudiante, Matricula.estado != "anulada")
        .order_by(
            PeriodoAcademico.anio.desc(),
            PeriodoAcademico.numero.desc(),
            Matricula.id_matricula.desc(),
        )
        .options(
            selectinload(Matricula.periodo),
            selectinload(Matricula.detalles).selectinload(DetalleMatricula.grupo).selectinload(Grupo.materia),
            selectinload(Matricula.detalles).selectinload(DetalleMatricula.grupo).selectinload(Grupo.horarios).selectinload(Horario.aula),
            selectinload(Matricula.detalles).selectinload(DetalleMatricula.calificaciones),
            selectinload(Matricula.pagos),
        )
    )

    detalles = matricula.detalles if matricula else []
    horarios = []
    for detalle in detalles:
        for horario in detalle.grupo.horarios:
            horarios.append(
                {
                    "materia": detalle.grupo.materia.nombre,
                    "codigo": detalle.grupo.materia.codigo,
                    "grupo": detalle.grupo.codigo,
                    "dia": horario.dia_semana,
                    "inicio": horario.hora_inicio.strftime("%H:%M"),
                    "fin": horario.hora_fin.strftime("%H:%M"),
                    "aula": horario.aula.nombre if horario.aula else "Sin aula",
                }
            )

    pagos = matricula.pagos if matricula else []
    pagos_pendientes = [p for p in pagos if p.estado == "pendiente"]
    estado_financiero = "Paz y Salvo" if not pagos_pendientes else "Pago pendiente"

    calificaciones = []
    for detalle in detalles:
        for calificacion in detalle.calificaciones:
            calificaciones.append(
                {
                    "materia": detalle.grupo.materia.nombre,
                    "codigo": detalle.grupo.materia.codigo,
                    "evaluacion": calificacion.evaluacion,
                    "nota": float(calificacion.nota),
                    "ponderacion": float(calificacion.ponderacion),
                    "fecha": calificacion.fecha,
                }
            )
    calificaciones.sort(key=lambda item: item["fecha"], reverse=True)

    return {
        "estudiante": student_out(estudiante),
        "periodo": {
            "id_periodo": matricula.periodo.id_periodo,
            "nombre": matricula.periodo.nombre,
            "matricula_abierta": matricula.periodo.matricula_abierta,
            "max_creditos": matricula.periodo.max_creditos,
        }
        if matricula
        else None,
        "matricula": {
            "id_matricula": matricula.id_matricula,
            "estado": matricula.estado,
            "fecha": matricula.fecha,
            "total_creditos": matricula.total_creditos,
        }
        if matricula
        else None,
        "resumen": {
            "creditos": matricula.total_creditos if matricula else 0,
            "asignaturas": len(detalles),
            "indice": float(estudiante.indice_academico or 0),
            "estado_financiero": estado_financiero,
        },
        "asignaturas": [
            {
                **group_out(db, detalle.grupo),
                "id_detalle": detalle.id_detalle,
                "nota_final": float(detalle.nota_final) if detalle.nota_final is not None else None,
                "estado_detalle": detalle.estado,
            }
            for detalle in detalles
        ],
        "horarios": horarios,
        "calificaciones": calificaciones,
        "pagos": [
            {
                "id_pago": pago.id_pago,
                "monto": float(pago.monto),
                "fecha": pago.fecha,
                "estado": pago.estado,
                "metodo": pago.metodo,
                "referencia": pago.referencia,
            }
            for pago in pagos
        ],
    }
