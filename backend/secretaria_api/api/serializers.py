"""Utilidades para convertir modelos a diccionarios listos para la API."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from ..models import (
    Auditoria,
    Estudiante,
    Grupo,
    Horario,
    Nodo,
    Profesor,
    TransaccionDistribuida,
    Usuario,
)
from ..services.enrollment_service import cupos_disponibles


def user_session(usuario: Usuario) -> dict:
    return {
        "id_usuario": usuario.id_usuario,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "cedula": usuario.cedula,
        "rol": usuario.rol.nombre,
        "rol_id": usuario.id_rol,
        "activo": usuario.activo,
        "id_estudiante": usuario.estudiante.id_estudiante if usuario.estudiante else None,
        "id_profesor": usuario.profesor.id_profesor if usuario.profesor else None,
        "ultimo_acceso": usuario.ultimo_acceso,
    }


def user_out(usuario: Usuario) -> dict:
    return {
        "id_usuario": usuario.id_usuario,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "cedula": usuario.cedula,
        "telefono": usuario.telefono,
        "activo": usuario.activo,
        "id_rol": usuario.id_rol,
        "rol": usuario.rol.nombre if usuario.rol else None,
        "id_sede": usuario.id_sede,
        "sede": usuario.sede.nombre if usuario.sede else None,
        "ultimo_acceso": usuario.ultimo_acceso,
    }


def student_out(estudiante: Estudiante) -> dict:
    return {
        "id_estudiante": estudiante.id_estudiante,
        "id_usuario": estudiante.id_usuario,
        "codigo": estudiante.codigo,
        "estado": estudiante.estado,
        "indice_academico": float(estudiante.indice_academico or 0),
        "anio_ingreso": estudiante.anio_ingreso,
        "id_carrera": estudiante.id_carrera,
        "carrera": estudiante.carrera.nombre if estudiante.carrera else None,
        "id_plan": estudiante.id_plan,
        "plan": estudiante.plan.nombre if estudiante.plan else None,
        "nombre": estudiante.usuario.nombre if estudiante.usuario else None,
        "email": estudiante.usuario.email if estudiante.usuario else None,
        "cedula": estudiante.usuario.cedula if estudiante.usuario else None,
        "telefono": estudiante.usuario.telefono if estudiante.usuario else None,
    }


def professor_out(profesor: Profesor) -> dict:
    return {
        "id_profesor": profesor.id_profesor,
        "id_usuario": profesor.id_usuario,
        "nombre": profesor.usuario.nombre if profesor.usuario else None,
        "email": profesor.usuario.email if profesor.usuario else None,
        "categoria": profesor.categoria,
        "dedicacion": profesor.dedicacion,
        "estado": profesor.estado,
        "id_sede": profesor.id_sede,
        "sede": profesor.usuario.sede.nombre if profesor.usuario and profesor.usuario.sede else None,
        "titulos": [
            {"titulo": t.titulo, "institucion": t.institucion, "anio": t.anio}
            for t in profesor.titulos
        ],
    }


def horario_out(horario: Horario) -> dict:
    return {
        "id_horario": horario.id_horario,
        "dia_semana": horario.dia_semana,
        "hora_inicio": horario.hora_inicio.strftime("%H:%M"),
        "hora_fin": horario.hora_fin.strftime("%H:%M"),
        "aula": horario.aula.nombre if horario.aula else None,
        "id_aula": horario.id_aula,
    }


def group_out(db: Session, grupo: Grupo, incluir_cupos: bool = True) -> dict:
    profesor_nombre = None
    if grupo.profesor and grupo.profesor.usuario:
        profesor_nombre = grupo.profesor.usuario.nombre
    datos = {
        "id_grupo": grupo.id_grupo,
        "codigo": grupo.codigo,
        "estado": grupo.estado,
        "cupo": grupo.cupo,
        "id_materia": grupo.id_materia,
        "materia": grupo.materia.nombre if grupo.materia else None,
        "codigo_materia": grupo.materia.codigo if grupo.materia else None,
        "creditos": grupo.materia.creditos if grupo.materia else 0,
        "id_periodo": grupo.id_periodo,
        "periodo": grupo.periodo.nombre if grupo.periodo else None,
        "id_sede": grupo.id_sede,
        "sede": grupo.sede.nombre if grupo.sede else None,
        "id_profesor": grupo.id_profesor,
        "profesor": profesor_nombre,
        "horarios": [horario_out(h) for h in grupo.horarios],
    }
    if incluir_cupos:
        disponibles = cupos_disponibles(db, grupo)
        datos["cupos_disponibles"] = disponibles
        datos["cupos_ocupados"] = grupo.cupo - disponibles
    return datos


def node_out(nodo: Nodo) -> dict:
    return {
        "id_nodo": nodo.id_nodo,
        "nombre": nodo.nombre,
        "rol": nodo.rol,
        "host": nodo.host,
        "estado": nodo.estado,
        "latencia_ms": nodo.latencia_ms,
        "replicacion_pct": float(nodo.replicacion_pct or 0),
        "id_sede": nodo.id_sede,
        "ultima_sincronizacion": nodo.ultima_sincronizacion,
    }


def transaction_out(tx: TransaccionDistribuida) -> dict:
    return {
        "id_transaccion": tx.id_transaccion,
        "codigo": tx.codigo,
        "tipo": tx.tipo,
        "estado": tx.estado,
        "nodos_involucrados": tx.nodos_involucrados,
        "detalle": tx.detalle,
        "iniciada_en": tx.iniciada_en,
        "finalizada_en": tx.finalizada_en,
    }


def audit_out(registro: Auditoria) -> dict:
    return {
        "id_auditoria": registro.id_auditoria,
        "id_usuario": registro.id_usuario,
        "usuario": registro.usuario.nombre if registro.usuario else "Sistema",
        "accion": registro.accion,
        "entidad": registro.entidad,
        "entidad_id": registro.entidad_id,
        "detalle": registro.detalle,
        "ip": registro.ip,
        "fecha": registro.fecha,
    }


def decimal_to_float(value: Decimal | float | None) -> float | None:
    if value is None:
        return None
    return float(value)
