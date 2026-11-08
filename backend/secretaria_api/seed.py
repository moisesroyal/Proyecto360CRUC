"""Carga idempotente de datos iniciales.

Ejecutar con: python -m secretaria_api.seed
"""
from __future__ import annotations

from datetime import date, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from .core.config import settings
from .core.database import SessionLocal
from .core.security import hash_password
from .models import (
    Aula,
    Auditoria,
    Calificacion,
    Carrera,
    DetalleMatricula,
    Escuela,
    Estudiante,
    EventoLog,
    Facultad,
    Grupo,
    Horario,
    Materia,
    Matricula,
    Nodo,
    Pago,
    PeriodoAcademico,
    Permiso,
    PlanEstudio,
    PlanMateria,
    Prerrequisito,
    Profesor,
    Rol,
    RolPermiso,
    Sede,
    TituloAcademico,
    TransaccionDistribuida,
    Usuario,
)

ROLES = [
    ("admin", "Administrador general del sistema"),
    ("admin_facultad", "Administrador de facultad"),
    ("coordinador", "Coordinador de carrera"),
    ("secretaria", "Secretaría académica"),
    ("profesor", "Docente con carga académica"),
    ("estudiante", "Estudiante matriculado"),
]

MODULOS = [
    "usuarios",
    "estructura",
    "planes",
    "periodos",
    "carga",
    "matricula",
    "calificaciones",
    "pagos",
    "auditoria",
    "infraestructura",
]
ACCIONES = ["C", "L", "A", "B"]

PERMISOS_POR_ROL: dict[str, dict[str, set[str]]] = {
    "admin": {modulo: set(ACCIONES) for modulo in MODULOS},
    "admin_facultad": {
        "usuarios": set(),
        "estructura": set(ACCIONES),
        "planes": set(ACCIONES),
        "periodos": set(ACCIONES),
        "carga": {"L"},
        "matricula": {"L"},
        "calificaciones": {"L"},
        "pagos": {"L"},
        "auditoria": {"L"},
        "infraestructura": {"L"},
    },
    "coordinador": {
        "usuarios": set(),
        "estructura": {"L"},
        "planes": {"L", "A"},
        "periodos": set(ACCIONES),
        "carga": set(ACCIONES),
        "matricula": {"L", "A"},
        "calificaciones": {"L"},
        "pagos": set(),
        "auditoria": set(),
        "infraestructura": {"L"},
    },
    "secretaria": {
        "usuarios": {"L"},
        "estructura": {"L"},
        "planes": {"L"},
        "periodos": {"L"},
        "carga": {"L"},
        "matricula": set(ACCIONES),
        "calificaciones": {"L", "A"},
        "pagos": set(ACCIONES),
        "auditoria": set(),
        "infraestructura": {"L"},
    },
    "profesor": {
        "usuarios": set(),
        "estructura": {"L"},
        "planes": {"L"},
        "periodos": {"L"},
        "carga": {"L"},
        "matricula": {"L"},
        "calificaciones": set(ACCIONES),
        "pagos": set(),
        "auditoria": set(),
        "infraestructura": {"L"},
    },
    "estudiante": {
        "usuarios": set(),
        "estructura": {"L"},
        "planes": {"L"},
        "periodos": {"L"},
        "carga": set(),
        "matricula": {"C", "L"},
        "calificaciones": {"L"},
        "pagos": {"L"},
        "auditoria": set(),
        "infraestructura": {"L"},
    },
}


def _get_or_create(db: Session, modelo, filtros: dict, **valores):
    instancia = db.scalar(select(modelo).filter_by(**filtros))
    if instancia:
        return instancia, False
    instancia = modelo(**filtros, **valores)
    db.add(instancia)
    db.flush()
    return instancia, True


def seed_roles_y_permisos(db: Session) -> None:
    roles: dict[str, Rol] = {}
    for nombre, descripcion in ROLES:
        rol, _ = _get_or_create(db, Rol, {"nombre": nombre}, descripcion=descripcion)
        roles[nombre] = rol

    permisos: dict[tuple[str, str], Permiso] = {}
    for modulo in MODULOS:
        for accion in ACCIONES:
            permiso, _ = _get_or_create(
                db,
                Permiso,
                {"modulo": modulo, "accion": accion},
                descripcion=f"{accion} en {modulo}",
            )
            permisos[(modulo, accion)] = permiso

    for nombre_rol, modulos in PERMISOS_POR_ROL.items():
        rol = roles[nombre_rol]
        for modulo, acciones in modulos.items():
            for accion in acciones:
                permiso = permisos[(modulo, accion)]
                existente = db.get(RolPermiso, (rol.id_rol, permiso.id_permiso))
                if not existente:
                    db.add(RolPermiso(id_rol=rol.id_rol, id_permiso=permiso.id_permiso))


def seed_estructura(db: Session) -> dict:
    sedes = {}
    for nombre, ciudad, provincia in [
        ("Panamá", "Ciudad de Panamá", "Panamá"),
        ("Coclé", "Penonomé", "Coclé"),
        ("Veraguas", "Santiago", "Veraguas"),
    ]:
        sede, _ = _get_or_create(
            db, Sede, {"nombre": nombre}, ciudad=ciudad, provincia=provincia
        )
        sedes[nombre] = sede

    facultad, _ = _get_or_create(
        db,
        Facultad,
        {"codigo": "FIE"},
        nombre="Facultad de Informática, Electrónica y Comunicación",
        id_sede=sedes["Coclé"].id_sede,
        descripcion="Facultad del Centro Regional Universitario de Coclé.",
    )
    escuela, _ = _get_or_create(
        db,
        Escuela,
        {"codigo": "INFO"},
        nombre="Escuela de Informática",
        id_facultad=facultad.id_facultad,
    )
    carrera, _ = _get_or_create(
        db,
        Carrera,
        {"codigo": "IS"},
        nombre="Ingeniería Informática",
        id_escuela=escuela.id_escuela,
        titulo="Licenciado en Ingeniería Informática",
    )
    plan, _ = _get_or_create(
        db,
        PlanEstudio,
        {"nombre": "Plan 2022", "id_carrera": carrera.id_carrera},
        anio=2022,
        creditos_totales=220,
        estado="activo",
    )

    materias_data = [
        ("IS-301", "Ingeniería de Software I", 4, 3, 2),
        ("IS-302", "Sistemas Operativos II", 4, 3, 2),
        ("IS-303", "Arquitectura de Computadoras", 3, 2, 1),
        ("IS-411", "Bases de Datos Distribuidas", 4, 3, 2),
        ("IS-412", "Procesos y Redes Estocásticas", 3, 2, 1),
        ("IS-413", "Simulación de Sistemas", 3, 2, 1),
        ("IS-414", "Redes de Computadoras", 3, 2, 1),
        ("IS-415", "Taller de Ingeniería de Software", 3, 1, 2),
        ("IS-416", "Seguridad Informática", 3, 2, 1),
    ]
    materias: dict[str, Materia] = {}
    for codigo, nombre, creditos, ht, hp in materias_data:
        materia, _ = _get_or_create(
            db,
            Materia,
            {"codigo": codigo},
            nombre=nombre,
            creditos=creditos,
            horas_teoricas=ht,
            horas_practicas=hp,
            descripcion=f"Asignatura {nombre} del plan de Ingeniería Informática.",
        )
        materias[codigo] = materia
        if not db.get(PlanMateria, (plan.id_plan, materia.id_materia)):
            db.add(
                PlanMateria(
                    id_plan=plan.id_plan,
                    id_materia=materia.id_materia,
                    nivel=max(1, int(codigo.split("-")[1][0]) - 2),
                    tipo="obligatoria",
                )
            )

    for materia_codigo, requisito_codigo in [
        ("IS-411", "IS-301"),
        ("IS-412", "IS-302"),
        ("IS-413", "IS-303"),
        ("IS-415", "IS-301"),
    ]:
        materia = materias[materia_codigo]
        requisito = materias[requisito_codigo]
        if not db.get(Prerrequisito, (materia.id_materia, requisito.id_materia)):
            db.add(
                Prerrequisito(
                    id_materia=materia.id_materia,
                    id_materia_requisito=requisito.id_materia,
                )
            )

    periodos = {}
    for nombre, anio, numero, inicio, fin, estado, abierto, max_creditos in [
        ("2025-II", 2025, 2, date(2025, 8, 1), date(2025, 12, 15), "cerrado", False, 24),
        ("2026-I", 2026, 1, date(2026, 3, 1), date(2026, 7, 15), "cerrado", False, 24),
        ("2026-II", 2026, 2, date(2026, 8, 1), date(2026, 12, 15), "abierto", True, 24),
        ("2027-I", 2027, 1, date(2027, 3, 1), date(2027, 7, 15), "planificado", False, 24),
    ]:
        periodo, _ = _get_or_create(
            db,
            PeriodoAcademico,
            {"nombre": nombre},
            anio=anio,
            numero=numero,
            tipo="semestre",
            fecha_inicio=inicio,
            fecha_fin=fin,
            estado=estado,
            matricula_abierta=abierto,
            max_creditos=max_creditos,
        )
        periodos[nombre] = periodo

    aulas = {}
    for nombre, sede, capacidad, tipo in [
        ("Aula 204 - Sistemas", "Coclé", 35, "aula"),
        ("Laboratorio de Cómputo 1", "Coclé", 30, "laboratorio"),
        ("Aula 102", "Coclé", 40, "aula"),
        ("Laboratorio de Redes", "Coclé", 25, "laboratorio"),
        ("Aula Magna Panamá", "Panamá", 80, "aula"),
        ("Aula 201 Veraguas", "Veraguas", 35, "aula"),
    ]:
        aula, _ = _get_or_create(
            db,
            Aula,
            {"id_sede": sedes[sede].id_sede, "nombre": nombre},
            capacidad=capacidad,
            tipo=tipo,
        )
        aulas[nombre] = aula

    return {
        "sedes": sedes,
        "facultad": facultad,
        "escuela": escuela,
        "carrera": carrera,
        "plan": plan,
        "materias": materias,
        "periodos": periodos,
        "aulas": aulas,
    }


def _crear_usuario(
    db: Session,
    roles: dict[str, Rol],
    *,
    nombre: str,
    email: str,
    cedula: str,
    password: str,
    rol: str,
    id_sede: int | None = None,
) -> Usuario:
    usuario, creado = _get_or_create(
        db,
        Usuario,
        {"email": email},
        id_rol=roles[rol].id_rol,
        nombre=nombre,
        cedula=cedula,
        password_hash=hash_password(password),
        id_sede=id_sede,
        activo=True,
    )
    if creado:
        db.flush()
    return usuario


def seed_personas(db: Session, base: dict) -> dict:
    roles = {rol.nombre: rol for rol in db.scalars(select(Rol)).all()}
    sede_cocle = base["sedes"]["Coclé"].id_sede

    admin = _crear_usuario(
        db,
        roles,
        nombre=settings.seed_admin_name,
        email=settings.seed_admin_email,
        cedula=settings.seed_admin_cedula,
        password=settings.seed_admin_password,
        rol="admin",
        id_sede=sede_cocle,
    )
    secretaria = _crear_usuario(
        db,
        roles,
        nombre="María González",
        email="secretaria@universidad.edu.pa",
        cedula="8-333-3333",
        password="password123",
        rol="secretaria",
        id_sede=sede_cocle,
    )
    ana = _crear_usuario(
        db,
        roles,
        nombre="Prof. Ana Gómez",
        email="ana.gomez@universidad.edu.pa",
        cedula="8-111-1111",
        password="password123",
        rol="profesor",
        id_sede=sede_cocle,
    )
    luis = _crear_usuario(
        db,
        roles,
        nombre="Ing. Luis Pérez",
        email="luis.perez@universidad.edu.pa",
        cedula="8-222-2222",
        password="password123",
        rol="profesor",
        id_sede=sede_cocle,
    )
    estudiante_user = _crear_usuario(
        db,
        roles,
        nombre=settings.seed_student_name,
        email=settings.seed_student_email,
        cedula=settings.seed_student_cedula,
        password=settings.seed_student_password,
        rol="estudiante",
        id_sede=sede_cocle,
    )
    juan = _crear_usuario(
        db,
        roles,
        nombre="Juan Batista",
        email="juan.batista@universidad.edu.pa",
        cedula="8-777-7777",
        password="password123",
        rol="estudiante",
        id_sede=sede_cocle,
    )

    def asegurar_profesor(usuario: Usuario, categoria: str, dedicacion: str) -> Profesor:
        profesor = db.scalar(select(Profesor).where(Profesor.id_usuario == usuario.id_usuario))
        if not profesor:
            profesor = Profesor(
                id_usuario=usuario.id_usuario,
                id_sede=usuario.id_sede,
                categoria=categoria,
                dedicacion=dedicacion,
                estado="activo",
            )
            db.add(profesor)
            db.flush()
        return profesor

    profesores = {
        "admin": asegurar_profesor(admin, "titular", "tiempo completo"),
        "ana": asegurar_profesor(ana, "asistente", "tiempo completo"),
        "luis": asegurar_profesor(luis, "auxiliar", "medio tiempo"),
    }
    for profesor, titulo, institucion, anio in [
        (profesores["admin"], "Doctor en Ciencias de la Computación", "Universidad de Panamá", 2012),
        (profesores["ana"], "Máster en Redes y Sistemas", "Universidad Tecnológica de Panamá", 2018),
        (profesores["luis"], "Licenciado en Informática", "Universidad de Panamá", 2015),
    ]:
        existente = db.scalar(
            select(TituloAcademico).where(
                TituloAcademico.id_profesor == profesor.id_profesor,
                TituloAcademico.titulo == titulo,
            )
        )
        if not existente:
            db.add(
                TituloAcademico(
                    id_profesor=profesor.id_profesor,
                    titulo=titulo,
                    institucion=institucion,
                    anio=anio,
                )
            )

    def asegurar_estudiante(usuario: Usuario, codigo: str, indice: float) -> Estudiante:
        estudiante = db.scalar(select(Estudiante).where(Estudiante.id_usuario == usuario.id_usuario))
        if not estudiante:
            estudiante = Estudiante(
                id_usuario=usuario.id_usuario,
                id_carrera=base["carrera"].id_carrera,
                id_plan=base["plan"].id_plan,
                codigo=codigo,
                estado="activo",
                indice_academico=indice,
                anio_ingreso=2022,
            )
            db.add(estudiante)
            db.flush()
        return estudiante

    estudiantes = {
        "ana": asegurar_estudiante(estudiante_user, "EST-2022-0001", 2.77),
        "juan": asegurar_estudiante(juan, "EST-2023-0002", 2.35),
    }

    return {
        "admin": admin,
        "secretaria": secretaria,
        "profesores": profesores,
        "estudiantes": estudiantes,
    }


def seed_oferta(db: Session, base: dict, personas: dict) -> list[Grupo]:
    sede_cocle = base["sedes"]["Coclé"].id_sede
    periodo = base["periodos"]["2026-II"]
    aulas = base["aulas"]
    materias = base["materias"]

    oferta = [
        ("IS-411", "IS-411-A", personas["profesores"]["admin"].id_profesor, 30, [
            ("Lunes", time(16, 0), time(18, 0), "Aula 204 - Sistemas"),
            ("Miércoles", time(16, 0), time(18, 0), "Aula 204 - Sistemas"),
        ]),
        ("IS-412", "IS-412-A", personas["profesores"]["ana"].id_profesor, 25, [
            ("Martes", time(14, 0), time(16, 0), "Laboratorio de Cómputo 1"),
            ("Jueves", time(14, 0), time(16, 0), "Laboratorio de Cómputo 1"),
        ]),
        ("IS-413", "IS-413-A", personas["profesores"]["luis"].id_profesor, 25, [
            ("Viernes", time(8, 0), time(12, 0), "Aula 102"),
        ]),
        ("IS-414", "IS-414-A", personas["profesores"]["ana"].id_profesor, 20, [
            ("Lunes", time(10, 0), time(12, 0), "Laboratorio de Redes"),
            ("Miércoles", time(10, 0), time(12, 0), "Laboratorio de Redes"),
        ]),
        ("IS-415", "IS-415-A", personas["profesores"]["luis"].id_profesor, 15, [
            ("Martes", time(8, 0), time(11, 0), "Aula 102"),
        ]),
        ("IS-416", "IS-416-A", personas["profesores"]["admin"].id_profesor, 20, [
            ("Jueves", time(10, 0), time(13, 0), "Laboratorio de Redes"),
        ]),
    ]

    grupos: list[Grupo] = []
    for codigo_materia, codigo_grupo, id_profesor, cupo, horarios in oferta:
        grupo, creado = _get_or_create(
            db,
            Grupo,
            {"id_periodo": periodo.id_periodo, "codigo": codigo_grupo},
            id_materia=materias[codigo_materia].id_materia,
            id_profesor=id_profesor,
            id_sede=sede_cocle,
            cupo=cupo,
            estado="abierto",
        )
        grupos.append(grupo)
        if creado:
            for dia, inicio, fin, aula_nombre in horarios:
                db.add(
                    Horario(
                        id_grupo=grupo.id_grupo,
                        id_aula=aulas[aula_nombre].id_aula,
                        dia_semana=dia,
                        hora_inicio=inicio,
                        hora_fin=fin,
                    )
                )
    db.flush()
    return grupos


def _asegurar_matricula(
    db: Session,
    estudiante: Estudiante,
    periodo: PeriodoAcademico,
    grupos: list[Grupo],
    estado: str,
) -> Matricula:
    matricula = db.scalar(
        select(Matricula).where(
            Matricula.id_estudiante == estudiante.id_estudiante,
            Matricula.id_periodo == periodo.id_periodo,
        )
    )
    if matricula:
        return matricula
    matricula = Matricula(
        id_estudiante=estudiante.id_estudiante,
        id_periodo=periodo.id_periodo,
        estado=estado,
        total_creditos=sum(grupo.materia.creditos for grupo in grupos),
    )
    db.add(matricula)
    db.flush()
    for grupo in grupos:
        db.add(
            DetalleMatricula(
                id_matricula=matricula.id_matricula,
                id_grupo=grupo.id_grupo,
                estado="inscrito",
            )
        )
    db.flush()
    return matricula


def seed_matriculas(db: Session, base: dict, grupos: list[Grupo]) -> None:
    ana = db.scalar(
        select(Estudiante).where(Estudiante.codigo == "EST-2022-0001")
    )
    juan = db.scalar(select(Estudiante).where(Estudiante.codigo == "EST-2023-0002"))
    if not ana:
        return

    grupos_por_codigo = {grupo.codigo: grupo for grupo in grupos}
    periodo_actual = base["periodos"]["2026-II"]
    periodo_anterior = base["periodos"]["2025-II"]

    grupos_pasados = []
    for codigo, nota in [("IS-301", 95.0), ("IS-302", 90.0), ("IS-303", 92.0)]:
        materia = base["materias"][codigo]
        grupo = db.scalar(
            select(Grupo).where(
                Grupo.id_periodo == periodo_anterior.id_periodo,
                Grupo.id_materia == materia.id_materia,
            )
        )
        if not grupo:
            grupo = Grupo(
                id_materia=materia.id_materia,
                id_periodo=periodo_anterior.id_periodo,
                id_sede=base["sedes"]["Coclé"].id_sede,
                id_profesor=None,
                codigo=f"{codigo}-H",
                cupo=30,
                estado="cerrado",
            )
            db.add(grupo)
            db.flush()
        grupos_pasados.append((grupo, nota))

    matricula_pasada = _asegurar_matricula(
        db, ana, periodo_anterior, [g for g, _ in grupos_pasados], "confirmada"
    )
    for grupo, nota in grupos_pasados:
        detalle = db.scalar(
            select(DetalleMatricula).where(
                DetalleMatricula.id_matricula == matricula_pasada.id_matricula,
                DetalleMatricula.id_grupo == grupo.id_grupo,
            )
        )
        if not detalle:
            continue
        if detalle.nota_final is None:
            detalle.nota_final = nota
        if not detalle.calificaciones:
            db.add(
                Calificacion(
                    id_detalle=detalle.id_detalle,
                    evaluacion="Nota final",
                    nota=nota,
                    ponderacion=100,
                    fecha=date(2025, 12, 10),
                    observacion="Calificación histórica de prueba",
                )
            )

    if matricula_pasada.pagos == [] or not matricula_pasada.pagos:
        db.add(
            Pago(
                id_matricula=matricula_pasada.id_matricula,
                monto=150.00,
                estado="pagado",
                metodo="transferencia",
                referencia="PAGO-2025-0001",
            )
        )

    grupos_actuales = [
        grupos_por_codigo["IS-411-A"],
        grupos_por_codigo["IS-412-A"],
        grupos_por_codigo["IS-413-A"],
    ]
    matricula_actual = _asegurar_matricula(
        db, ana, periodo_actual, grupos_actuales, "pendiente"
    )
    if not matricula_actual.pagos:
        db.add(
            Pago(
                id_matricula=matricula_actual.id_matricula,
                monto=150.00,
                estado="pendiente",
                metodo="transferencia",
                referencia="PAGO-2026-0001",
            )
        )

    if juan:
        grupos_juan = [grupos_por_codigo["IS-414-A"]]
        _asegurar_matricula(db, juan, periodo_actual, grupos_juan, "pendiente")


def seed_infraestructura(db: Session) -> None:
    for nombre, rol, latencia, replicacion in [
        ("Panamá", "Información institucional", 18, 100),
        ("Coclé", "Estudiantes y cursos regionales", 16, 98),
        ("Veraguas", "Estudiantes y cursos regionales", 12, 100),
    ]:
        _get_or_create(
            db,
            Nodo,
            {"nombre": nombre},
            rol=rol,
            host=f"{nombre.lower()}.universidad.local",
            estado="online",
            latencia_ms=latencia,
            replicacion_pct=replicacion,
        )

    for codigo, tipo, estado, nodos, detalle in [
        ("TXN-1041", "Actualización", "PREPARE", 3, "Sincronización de matrícula entre sedes"),
        ("TXN-1039", "Consulta", "COMMIT", 2, "Consulta global de estudiantes"),
        ("TXN-1038", "Consulta", "EJECUTANDO", 1, "Listado de oferta académica"),
    ]:
        _get_or_create(
            db,
            TransaccionDistribuida,
            {"codigo": codigo},
            tipo=tipo,
            estado=estado,
            nodos_involucrados=nodos,
            detalle=detalle,
        )

    if not db.scalar(select(EventoLog).limit(1)):
        db.add(
            EventoLog(
                nivel="INFO",
                origen="seed",
                mensaje="Base de datos inicializada con datos de demostración.",
            )
        )
    if not db.scalar(select(Auditoria).limit(1)):
        db.add(
            Auditoria(
                accion="CREAR",
                entidad="sistema",
                detalle="Carga inicial de datos",
                ip="127.0.0.1",
            )
        )


def run() -> None:
    db = SessionLocal()
    try:
        seed_roles_y_permisos(db)
        base = seed_estructura(db)
        personas = seed_personas(db, base)
        grupos = seed_oferta(db, base, personas)
        seed_matriculas(db, base, grupos)
        seed_infraestructura(db)
        db.commit()
        print("Datos iniciales cargados correctamente.")
        print(f"Admin: {settings.seed_admin_email} / {settings.seed_admin_password}")
        print(f"Estudiante: {settings.seed_student_email} / {settings.seed_student_password}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
