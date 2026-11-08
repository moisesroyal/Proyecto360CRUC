from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ...core.database import get_db
from ...models import (
    Aula,
    Carrera,
    DetalleMatricula,
    Escuela,
    Estudiante,
    Facultad,
    Grupo,
    Horario,
    Materia,
    Matricula,
    PeriodoAcademico,
    PlanEstudio,
    PlanMateria,
    Prerrequisito,
    Profesor,
    Sede,
    Usuario,
)
from ...schemas.academic import (
    AulaCreate,
    CarreraCreate,
    EscuelaCreate,
    FacultadCreate,
    GrupoCreate,
    MateriaCreate,
    PeriodoCreate,
    PlanCreate,
    PlanMateriaCreate,
    PrerrequisitoCreate,
    SedeCreate,
)
from ...services.audit import registrar_auditoria
from ...services.enrollment_service import (
    EnrollmentError,
    cupos_disponibles,
    materias_aprobadas,
    prerrequisitos_pendientes,
)
from ..deps import get_current_user, require_admin
from ..serializers import group_out

router = APIRouter(prefix="/academic", tags=["Estructura académica"])


def _commit(db: Session, entidad, usuario: Usuario, accion: str, nombre: str):
    registrar_auditoria(db, usuario, accion, nombre, getattr(entidad, "id_" + nombre, None))
    db.commit()
    db.refresh(entidad)


@router.get("/catalog")
def catalog(
    _: Usuario = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    return {
        "sedes": [
            {"id_sede": s.id_sede, "nombre": s.nombre}
            for s in db.scalars(select(Sede).order_by(Sede.nombre)).all()
        ],
        "facultades": [
            {"id_facultad": f.id_facultad, "nombre": f.nombre, "codigo": f.codigo}
            for f in db.scalars(select(Facultad).order_by(Facultad.nombre)).all()
        ],
        "escuelas": [
            {
                "id_escuela": e.id_escuela,
                "nombre": e.nombre,
                "id_facultad": e.id_facultad,
            }
            for e in db.scalars(select(Escuela).order_by(Escuela.nombre)).all()
        ],
        "carreras": [
            {
                "id_carrera": c.id_carrera,
                "nombre": c.nombre,
                "codigo": c.codigo,
                "id_escuela": c.id_escuela,
            }
            for c in db.scalars(select(Carrera).order_by(Carrera.nombre)).all()
        ],
        "planes": [
            {
                "id_plan": p.id_plan,
                "nombre": p.nombre,
                "anio": p.anio,
                "id_carrera": p.id_carrera,
            }
            for p in db.scalars(select(PlanEstudio).order_by(PlanEstudio.anio.desc())).all()
        ],
        "materias": [
            {
                "id_materia": m.id_materia,
                "codigo": m.codigo,
                "nombre": m.nombre,
                "creditos": m.creditos,
            }
            for m in db.scalars(select(Materia).order_by(Materia.codigo)).all()
        ],
        "periodos": [
            {
                "id_periodo": p.id_periodo,
                "nombre": p.nombre,
                "estado": p.estado,
                "matricula_abierta": p.matricula_abierta,
                "max_creditos": p.max_creditos,
            }
            for p in db.scalars(
                select(PeriodoAcademico).order_by(
                    PeriodoAcademico.anio.desc(), PeriodoAcademico.numero.desc()
                )
            ).all()
        ],
        "aulas": [
            {
                "id_aula": a.id_aula,
                "nombre": a.nombre,
                "id_sede": a.id_sede,
                "capacidad": a.capacidad,
            }
            for a in db.scalars(select(Aula).order_by(Aula.nombre)).all()
        ],
    }


# --------------------------------------------------------------------------- sedes
@router.get("/sedes")
def listar_sedes(_: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return [
        {
            "id_sede": s.id_sede,
            "nombre": s.nombre,
            "ciudad": s.ciudad,
            "provincia": s.provincia,
            "activo": s.activo,
        }
        for s in db.scalars(select(Sede).order_by(Sede.nombre)).all()
    ]


@router.post("/sedes", status_code=status.HTTP_201_CREATED)
def crear_sede(
    payload: SedeCreate,
    usuario: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    sede = Sede(**payload.model_dump())
    db.add(sede)
    db.flush()
    _commit(db, sede, usuario, "CREAR", "sede")
    return {"id_sede": sede.id_sede, "nombre": sede.nombre}


# ------------------------------------------------------------------------ facultades
@router.get("/facultades")
def listar_facultades(_: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return [
        {
            "id_facultad": f.id_facultad,
            "nombre": f.nombre,
            "codigo": f.codigo,
            "id_sede": f.id_sede,
            "sede": f.sede.nombre if f.sede else None,
            "activo": f.activo,
        }
        for f in db.scalars(select(Facultad).order_by(Facultad.nombre)).all()
    ]


@router.post("/facultades", status_code=status.HTTP_201_CREATED)
def crear_facultad(
    payload: FacultadCreate,
    usuario: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    facultad = Facultad(**payload.model_dump())
    db.add(facultad)
    db.flush()
    _commit(db, facultad, usuario, "CREAR", "facultad")
    return {"id_facultad": facultad.id_facultad, "nombre": facultad.nombre}


# ---------------------------------------------------------------------------- escuelas
@router.get("/escuelas")
def listar_escuelas(_: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return [
        {
            "id_escuela": e.id_escuela,
            "nombre": e.nombre,
            "codigo": e.codigo,
            "id_facultad": e.id_facultad,
            "facultad": e.facultad.nombre if e.facultad else None,
        }
        for e in db.scalars(select(Escuela).order_by(Escuela.nombre)).all()
    ]


@router.post("/escuelas", status_code=status.HTTP_201_CREATED)
def crear_escuela(
    payload: EscuelaCreate,
    usuario: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not db.get(Facultad, payload.id_facultad):
        raise HTTPException(status_code=404, detail="Facultad no encontrada.")
    escuela = Escuela(**payload.model_dump())
    db.add(escuela)
    db.flush()
    _commit(db, escuela, usuario, "CREAR", "escuela")
    return {"id_escuela": escuela.id_escuela, "nombre": escuela.nombre}


# ----------------------------------------------------------------------------- carreras
@router.get("/carreras")
def listar_carreras(_: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return [
        {
            "id_carrera": c.id_carrera,
            "nombre": c.nombre,
            "codigo": c.codigo,
            "titulo": c.titulo,
            "id_escuela": c.id_escuela,
            "escuela": c.escuela.nombre if c.escuela else None,
            "activo": c.activo,
        }
        for c in db.scalars(select(Carrera).order_by(Carrera.nombre)).all()
    ]


@router.post("/carreras", status_code=status.HTTP_201_CREATED)
def crear_carrera(
    payload: CarreraCreate,
    usuario: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not db.get(Escuela, payload.id_escuela):
        raise HTTPException(status_code=404, detail="Escuela no encontrada.")
    carrera = Carrera(**payload.model_dump())
    db.add(carrera)
    db.flush()
    _commit(db, carrera, usuario, "CREAR", "carrera")
    return {"id_carrera": carrera.id_carrera, "nombre": carrera.nombre}


# ------------------------------------------------------------------------------- planes
@router.get("/planes")
def listar_planes(_: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return [
        {
            "id_plan": p.id_plan,
            "nombre": p.nombre,
            "anio": p.anio,
            "creditos_totales": p.creditos_totales,
            "estado": p.estado,
            "id_carrera": p.id_carrera,
            "carrera": p.carrera.nombre if p.carrera else None,
        }
        for p in db.scalars(select(PlanEstudio).order_by(PlanEstudio.anio.desc())).all()
    ]


@router.post("/planes", status_code=status.HTTP_201_CREATED)
def crear_plan(
    payload: PlanCreate,
    usuario: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not db.get(Carrera, payload.id_carrera):
        raise HTTPException(status_code=404, detail="Carrera no encontrada.")
    plan = PlanEstudio(**payload.model_dump())
    db.add(plan)
    db.flush()
    _commit(db, plan, usuario, "CREAR", "plan_estudio")
    return {"id_plan": plan.id_plan, "nombre": plan.nombre}


# ----------------------------------------------------------------------------- materias
@router.get("/materias")
def listar_materias(_: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return [
        {
            "id_materia": m.id_materia,
            "codigo": m.codigo,
            "nombre": m.nombre,
            "creditos": m.creditos,
            "horas_teoricas": m.horas_teoricas,
            "horas_practicas": m.horas_practicas,
            "activo": m.activo,
            "prerequisitos": [
                {
                    "codigo": p.materia_requisito.codigo,
                    "nombre": p.materia_requisito.nombre,
                }
                for p in m.prerequisitos
            ],
        }
        for m in db.scalars(
            select(Materia).options(
                selectinload(Materia.prerequisitos).selectinload(Prerrequisito.materia_requisito)
            ).order_by(Materia.codigo)
        ).all()
    ]


@router.post("/materias", status_code=status.HTTP_201_CREATED)
def crear_materia(
    payload: MateriaCreate,
    usuario: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.scalar(select(Materia).where(Materia.codigo == payload.codigo)):
        raise HTTPException(status_code=409, detail="Ya existe una materia con ese código.")
    materia = Materia(**payload.model_dump())
    db.add(materia)
    db.flush()
    _commit(db, materia, usuario, "CREAR", "materia")
    return {"id_materia": materia.id_materia, "codigo": materia.codigo}


@router.post("/planes/materias", status_code=status.HTTP_201_CREATED)
def agregar_materia_plan(
    payload: PlanMateriaCreate,
    usuario: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not db.get(PlanEstudio, payload.id_plan) or not db.get(Materia, payload.id_materia):
        raise HTTPException(status_code=404, detail="Plan o materia no encontrada.")
    existente = db.get(PlanMateria, (payload.id_plan, payload.id_materia))
    if existente:
        raise HTTPException(status_code=409, detail="La materia ya está en el plan.")
    plan_materia = PlanMateria(**payload.model_dump())
    db.add(plan_materia)
    registrar_auditoria(
        db, usuario, "CREAR", "plan_materia", f"{payload.id_plan}-{payload.id_materia}"
    )
    db.commit()
    return {"ok": True}


@router.post("/prerrequisitos", status_code=status.HTTP_201_CREATED)
def crear_prerrequisito(
    payload: PrerrequisitoCreate,
    usuario: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if payload.id_materia == payload.id_materia_requisito:
        raise HTTPException(status_code=400, detail="Una materia no puede ser su propio prerrequisito.")
    if not db.get(Materia, payload.id_materia) or not db.get(Materia, payload.id_materia_requisito):
        raise HTTPException(status_code=404, detail="Materia no encontrada.")
    if db.get(Prerrequisito, (payload.id_materia, payload.id_materia_requisito)):
        raise HTTPException(status_code=409, detail="El prerrequisito ya existe.")
    requisito = Prerrequisito(**payload.model_dump())
    db.add(requisito)
    registrar_auditoria(
        db, usuario, "CREAR", "prerrequisito", f"{payload.id_materia}-{payload.id_materia_requisito}"
    )
    db.commit()
    return {"ok": True}


# ----------------------------------------------------------------------------- períodos
@router.get("/periodos")
def listar_periodos(_: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return [
        {
            "id_periodo": p.id_periodo,
            "nombre": p.nombre,
            "anio": p.anio,
            "numero": p.numero,
            "tipo": p.tipo,
            "fecha_inicio": p.fecha_inicio,
            "fecha_fin": p.fecha_fin,
            "estado": p.estado,
            "matricula_abierta": p.matricula_abierta,
            "max_creditos": p.max_creditos,
        }
        for p in db.scalars(
            select(PeriodoAcademico).order_by(
                PeriodoAcademico.anio.desc(), PeriodoAcademico.numero.desc()
            )
        ).all()
    ]


@router.post("/periodos", status_code=status.HTTP_201_CREATED)
def crear_periodo(
    payload: PeriodoCreate,
    usuario: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if payload.fecha_fin < payload.fecha_inicio:
        raise HTTPException(status_code=400, detail="La fecha fin no puede ser anterior al inicio.")
    periodo = PeriodoAcademico(**payload.model_dump())
    db.add(periodo)
    db.flush()
    _commit(db, periodo, usuario, "CREAR", "periodo_academico")
    return {"id_periodo": periodo.id_periodo, "nombre": periodo.nombre}


@router.patch("/periodos/{id_periodo}/matricula")
def toggle_matricula(
    id_periodo: int,
    usuario: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    periodo = db.get(PeriodoAcademico, id_periodo)
    if not periodo:
        raise HTTPException(status_code=404, detail="Período no encontrado.")
    periodo.matricula_abierta = not periodo.matricula_abierta
    periodo.estado = "abierto" if periodo.matricula_abierta else "cerrado"
    registrar_auditoria(
        db,
        usuario,
        "ACTUALIZAR",
        "periodo_academico",
        periodo.id_periodo,
        f"Matrícula {'abierta' if periodo.matricula_abierta else 'cerrada'}",
    )
    db.commit()
    return {"id_periodo": periodo.id_periodo, "matricula_abierta": periodo.matricula_abierta}


# --------------------------------------------------------------------------------- aulas
@router.get("/aulas")
def listar_aulas(_: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return [
        {
            "id_aula": a.id_aula,
            "nombre": a.nombre,
            "capacidad": a.capacidad,
            "tipo": a.tipo,
            "id_sede": a.id_sede,
            "sede": a.sede.nombre if a.sede else None,
        }
        for a in db.scalars(select(Aula).order_by(Aula.nombre)).all()
    ]


@router.post("/aulas", status_code=status.HTTP_201_CREATED)
def crear_aula(
    payload: AulaCreate,
    usuario: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not db.get(Sede, payload.id_sede):
        raise HTTPException(status_code=404, detail="Sede no encontrada.")
    aula = Aula(**payload.model_dump())
    db.add(aula)
    db.flush()
    _commit(db, aula, usuario, "CREAR", "aula")
    return {"id_aula": aula.id_aula, "nombre": aula.nombre}


# ------------------------------------------------------------------------------- grupos
def _grupo_query():
    return select(Grupo).options(
        selectinload(Grupo.materia),
        selectinload(Grupo.periodo),
        selectinload(Grupo.sede),
        selectinload(Grupo.profesor).selectinload(Profesor.usuario),
        selectinload(Grupo.horarios).selectinload(Horario.aula),
    )


@router.get("/grupos")
def listar_grupos(
    periodo_id: int | None = Query(default=None),
    materia_id: int | None = Query(default=None),
    sede_id: int | None = Query(default=None),
    _: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    consulta = _grupo_query()
    if periodo_id:
        consulta = consulta.where(Grupo.id_periodo == periodo_id)
    if materia_id:
        consulta = consulta.where(Grupo.id_materia == materia_id)
    if sede_id:
        consulta = consulta.where(Grupo.id_sede == sede_id)
    grupos = db.scalars(consulta.order_by(Grupo.codigo)).all()
    return [group_out(db, grupo) for grupo in grupos]


@router.post("/grupos", status_code=status.HTTP_201_CREATED)
def crear_grupo(
    payload: GrupoCreate,
    usuario: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not db.get(Materia, payload.id_materia):
        raise HTTPException(status_code=404, detail="Materia no encontrada.")
    if not db.get(PeriodoAcademico, payload.id_periodo):
        raise HTTPException(status_code=404, detail="Período no encontrado.")
    if not db.get(Sede, payload.id_sede):
        raise HTTPException(status_code=404, detail="Sede no encontrada.")

    grupo = Grupo(
        id_materia=payload.id_materia,
        id_periodo=payload.id_periodo,
        id_sede=payload.id_sede,
        id_profesor=payload.id_profesor,
        codigo=payload.codigo,
        cupo=payload.cupo,
        estado="abierto",
    )
    db.add(grupo)
    db.flush()

    for horario in payload.horarios:
        if horario.hora_inicio >= horario.hora_fin:
            raise HTTPException(status_code=400, detail="La hora de inicio debe ser menor a la de fin.")
        aula = db.get(Aula, horario.id_aula)
        if not aula:
            raise HTTPException(status_code=404, detail="Aula no encontrada.")
        if aula.id_sede != payload.id_sede:
            raise HTTPException(status_code=400, detail="El aula no pertenece a la sede del grupo.")
        db.add(
            Horario(
                id_grupo=grupo.id_grupo,
                id_aula=horario.id_aula,
                dia_semana=horario.dia_semana,
                hora_inicio=horario.hora_inicio,
                hora_fin=horario.hora_fin,
            )
        )

    registrar_auditoria(db, usuario, "CREAR", "grupo", grupo.id_grupo, f"Grupo {grupo.codigo}")
    db.commit()
    grupo = db.scalar(_grupo_query().where(Grupo.id_grupo == grupo.id_grupo))
    return group_out(db, grupo)


@router.get("/ofertas")
def ofertas_disponibles(
    periodo_id: int | None = Query(default=None),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    estudiante = db.scalar(select(Estudiante).where(Estudiante.id_usuario == usuario.id_usuario))
    if not estudiante:
        raise HTTPException(status_code=403, detail="Solo los estudiantes pueden ver la oferta.")

    if periodo_id is None:
        periodo = db.scalar(
            select(PeriodoAcademico)
            .where(PeriodoAcademico.matricula_abierta.is_(True))
            .order_by(PeriodoAcademico.anio.desc(), PeriodoAcademico.numero.desc())
            .limit(1)
        )
        if not periodo:
            raise HTTPException(status_code=404, detail="No hay un período con matrícula abierta.")
        periodo_id = periodo.id_periodo

    grupos = db.scalars(
        _grupo_query()
        .where(Grupo.id_periodo == periodo_id, Grupo.estado == "abierto")
        .order_by(Grupo.codigo)
    ).all()

    matriculados = set(
        db.scalars(
            select(DetalleMatricula.id_grupo)
            .join(Matricula, Matricula.id_matricula == DetalleMatricula.id_matricula)
            .where(
                Matricula.id_estudiante == estudiante.id_estudiante,
                Matricula.id_periodo == periodo_id,
                Matricula.estado != "anulada",
            )
        ).all()
    )
    aprobadas = materias_aprobadas(db, estudiante)

    resultado = []
    for grupo in grupos:
        pendientes = prerrequisitos_pendientes(db, estudiante, grupo.materia)
        disponible = cupos_disponibles(db, grupo)
        ya = grupo.id_grupo in matriculados
        puede = (
            not ya
            and not pendientes
            and disponible > 0
            and grupo.estado == "abierto"
        )
        motivo = ""
        if ya:
            motivo = "Ya está matriculada"
        elif pendientes:
            motivo = "Prerrequisitos pendientes: " + ", ".join(pendientes)
        elif disponible <= 0:
            motivo = "Sin cupos disponibles"
        resultado.append(
            {
                **group_out(db, grupo),
                "ya_matriculada": ya,
                "prerequisitos_pendientes": pendientes,
                "puede_matricular": puede,
                "motivo": motivo,
                "prerequisito_aprobado": grupo.id_materia in aprobadas,
            }
        )
    return resultado
