"""Reglas de negocio para matrícula de estudiantes."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..models import (
    DetalleMatricula,
    Estudiante,
    Grupo,
    Horario,
    Matricula,
    Materia,
    PeriodoAcademico,
    Prerrequisito,
    Profesor,
    Usuario,
)


class EnrollmentError(ValueError):
    """Error de validación de matrícula con mensaje legible."""


def obtener_estudiante(db: Session, usuario: Usuario) -> Estudiante:
    estudiante = db.scalar(select(Estudiante).where(Estudiante.id_usuario == usuario.id_usuario))
    if not estudiante:
        raise EnrollmentError("El usuario actual no tiene expediente de estudiante.")
    return estudiante


def cupos_ocupados(db: Session, id_grupo: int) -> int:
    return int(
        db.scalar(
            select(func.count(DetalleMatricula.id_detalle)).where(
                DetalleMatricula.id_grupo == id_grupo,
                DetalleMatricula.estado == "inscrito",
            )
        )
        or 0
    )


def cupos_disponibles(db: Session, grupo: Grupo) -> int:
    return max(grupo.cupo - cupos_ocupados(db, grupo.id_grupo), 0)


def materias_aprobadas(db: Session, estudiante: Estudiante) -> set[int]:
    filas = db.execute(
        select(Grupo.id_materia)
        .join(DetalleMatricula, DetalleMatricula.id_grupo == Grupo.id_grupo)
        .join(Matricula, Matricula.id_matricula == DetalleMatricula.id_matricula)
        .where(
            Matricula.id_estudiante == estudiante.id_estudiante,
            Matricula.estado != "anulada",
            DetalleMatricula.estado == "inscrito",
            DetalleMatricula.nota_final.is_not(None),
            DetalleMatricula.nota_final >= 71,
        )
    ).all()
    return {fila[0] for fila in filas}


def prerrequisitos_pendientes(
    db: Session, estudiante: Estudiante, materia: Materia
) -> list[str]:
    requisitos = db.scalars(
        select(Prerrequisito).where(Prerrequisito.id_materia == materia.id_materia)
    ).all()
    if not requisitos:
        return []

    aprobadas = materias_aprobadas(db, estudiante)
    pendientes: list[str] = []
    for requisito in requisitos:
        if requisito.id_materia_requisito not in aprobadas:
            requerida = db.get(Materia, requisito.id_materia_requisito)
            pendientes.append(f"{requerida.codigo} - {requerida.nombre}" if requerida else str(requisito.id_materia_requisito))
    return pendientes


def _franjas(grupos: list[Grupo]) -> list[tuple[str, object, object, str]]:
    franjas: list[tuple[str, object, object, str]] = []
    for grupo in grupos:
        for horario in grupo.horarios:
            franjas.append(
                (horario.dia_semana, horario.hora_inicio, horario.hora_fin, grupo.codigo)
            )
    return franjas


def _solapan(inicio_a, fin_a, inicio_b, fin_b) -> bool:
    return inicio_a < fin_b and inicio_b < fin_a


def choques_horario(db: Session, estudiante: Estudiante, grupos: list[Grupo]) -> list[str]:
    franjas = _franjas(grupos)
    choques: list[str] = []
    for i in range(len(franjas)):
        for j in range(i + 1, len(franjas)):
            dia_a, ini_a, fin_a, cod_a = franjas[i]
            dia_b, ini_b, fin_b, cod_b = franjas[j]
            if dia_a == dia_b and _solapan(ini_a, fin_a, ini_b, fin_b):
                choques.append(f"Choque el {dia_a}: grupo {cod_a} con grupo {cod_b}")
    return choques


def grupos_matriculados(
    db: Session, estudiante: Estudiante, id_periodo: int, excluir_matricula: int | None = None
) -> list[Grupo]:
    consulta = (
        select(Grupo)
        .join(DetalleMatricula, DetalleMatricula.id_grupo == Grupo.id_grupo)
        .join(Matricula, Matricula.id_matricula == DetalleMatricula.id_matricula)
        .where(
            Matricula.id_estudiante == estudiante.id_estudiante,
            Matricula.id_periodo == id_periodo,
            Matricula.estado != "anulada",
            DetalleMatricula.estado == "inscrito",
        )
        .options(selectinload(Grupo.horarios))
    )
    if excluir_matricula is not None:
        consulta = consulta.where(Matricula.id_matricula != excluir_matricula)
    return list(db.scalars(consulta).unique().all())


def matricular(
    db: Session,
    usuario: Usuario,
    id_periodo: int,
    id_grupos: list[int],
    ip: str | None = None,
) -> tuple[Matricula, list[str]]:
    from .audit import registrar_auditoria, registrar_evento

    estudiante = obtener_estudiante(db, usuario)
    periodo = db.get(PeriodoAcademico, id_periodo)
    if not periodo:
        raise EnrollmentError("El período académico no existe.")
    if not periodo.matricula_abierta or periodo.estado != "abierto":
        raise EnrollmentError("La matrícula de este período no está abierta.")

    if estudiante.estado != "activo":
        raise EnrollmentError("El expediente del estudiante no está activo.")

    ids_unicos = list(dict.fromkeys(id_grupos))
    if not ids_unicos:
        raise EnrollmentError("Debe seleccionar al menos un grupo.")

    grupos = list(
        db.scalars(
            select(Grupo)
            .where(Grupo.id_grupo.in_(ids_unicos))
            .options(
                selectinload(Grupo.materia),
                selectinload(Grupo.horarios),
                selectinload(Grupo.periodo),
                selectinload(Grupo.profesor).selectinload(Profesor.usuario),
            )
        ).all()
    )
    if len(grupos) != len(ids_unicos):
        raise EnrollmentError("Uno o más grupos seleccionados no existen.")

    for grupo in grupos:
        if grupo.id_periodo != id_periodo:
            raise EnrollmentError("Todos los grupos deben pertenecer al mismo período.")
        if grupo.estado != "abierto":
            raise EnrollmentError(f"El grupo {grupo.codigo} no está abierto.")
        if cupos_disponibles(db, grupo) <= 0:
            raise EnrollmentError(f"El grupo {grupo.codigo} no tiene cupos disponibles.")
        pendientes = prerrequisitos_pendientes(db, estudiante, grupo.materia)
        if pendientes:
            raise EnrollmentError(
                f"No cumple prerrequisitos para {grupo.materia.codigo}: "
                + ", ".join(pendientes)
            )

    matricula = db.scalar(
        select(Matricula)
        .where(
            Matricula.id_estudiante == estudiante.id_estudiante,
            Matricula.id_periodo == id_periodo,
        )
        .options(selectinload(Matricula.detalles))
    )
    if matricula and matricula.estado == "confirmada":
        raise EnrollmentError(
            "La matrícula de este período ya está confirmada. Contacte a Secretaría."
        )
    if matricula and matricula.estado == "anulada":
        raise EnrollmentError("La matrícula de este período fue anulada. Contacte a Secretaría.")

    existentes = grupos_matriculados(db, estudiante, id_periodo, matricula.id_matricula if matricula else None)
    ya_incluidos = {detalle.id_grupo for detalle in matricula.detalles} if matricula else set()

    nuevos = [grupo for grupo in grupos if grupo.id_grupo not in ya_incluidos]
    if not nuevos and matricula:
        raise EnrollmentError("Los grupos seleccionados ya están matriculados.")

    choques = choques_horario(db, estudiante, existentes + nuevos)
    if choques:
        raise EnrollmentError("; ".join(choques))

    creditos_actuales = sum(d.grupo.materia.creditos for d in matricula.detalles) if matricula else 0
    creditos_nuevos = creditos_actuales + sum(g.materia.creditos for g in nuevos)
    if creditos_nuevos > periodo.max_creditos:
        raise EnrollmentError(
            f"El total de créditos ({creditos_nuevos}) supera el máximo permitido "
            f"({periodo.max_creditos})."
        )

    advertencias: list[str] = []
    for grupo in nuevos:
        disponibles = cupos_disponibles(db, grupo)
        if disponibles <= 2:
            advertencias.append(f"El grupo {grupo.codigo} tiene solo {disponibles} cupo(s).")

    if not matricula:
        matricula = Matricula(
            id_estudiante=estudiante.id_estudiante,
            id_periodo=id_periodo,
            estado="pendiente",
            total_creditos=0,
        )
        db.add(matricula)
        db.flush()

    for grupo in nuevos:
        db.add(
            DetalleMatricula(
                id_matricula=matricula.id_matricula,
                id_grupo=grupo.id_grupo,
                estado="inscrito",
            )
        )

    db.flush()
    matricula.total_creditos = creditos_nuevos
    registrar_auditoria(
        db,
        usuario,
        "CREAR",
        "matricula",
        matricula.id_matricula,
        detalle=f"Grupos: {', '.join(g.codigo for g in nuevos)}; créditos={creditos_nuevos}",
        ip=ip,
    )
    registrar_evento(
        db,
        f"Matrícula {matricula.id_matricula} actualizada con {len(nuevos)} asignatura(s).",
        origen="matricula",
    )
    db.commit()
    db.refresh(matricula)
    return matricula, advertencias
