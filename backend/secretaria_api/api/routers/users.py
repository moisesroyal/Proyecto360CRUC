from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ...core.database import get_db
from ...core.security import hash_password
from ...models import (
    Carrera,
    Estudiante,
    Permiso,
    PlanEstudio,
    Profesor,
    Rol,
    RolPermiso,
    Usuario,
)
from ...schemas.people import UsuarioCreate, UsuarioStatusUpdate
from ...services.audit import registrar_auditoria
from ..deps import (
    get_client_ip,
    get_current_user,
    require_admin,
    require_roles,
    require_superadmin,
)
from ..serializers import professor_out, student_out, user_out

router = APIRouter(prefix="/users", tags=["Usuarios y roles"])

STAFF_ROLE_NAMES = {"admin", "admin_facultad", "coordinador", "secretaria"}
DIRECTORY_ROLES = ("admin", "admin_facultad", "coordinador")


@router.get("")
def listar_usuarios(
    rol: str | None = Query(default=None),
    activo: bool | None = Query(default=None),
    _: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    consulta = select(Usuario).options(
        selectinload(Usuario.rol), selectinload(Usuario.sede)
    )
    if rol:
        consulta = consulta.join(Rol, Rol.id_rol == Usuario.id_rol).where(
            func.lower(Rol.nombre) == rol.lower()
        )
    if activo is not None:
        consulta = consulta.where(Usuario.activo.is_(activo))
    usuarios = db.scalars(consulta.order_by(Usuario.nombre)).unique().all()
    return [user_out(usuario) for usuario in usuarios]


@router.get("/roles")
def listar_roles(_: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    roles = db.scalars(select(Rol).options(selectinload(Rol.permisos)).order_by(Rol.nombre)).all()
    return [
        {
            "id_rol": rol.id_rol,
            "nombre": rol.nombre,
            "descripcion": rol.descripcion,
            "permisos": [
                {"modulo": rp.permiso.modulo, "accion": rp.permiso.accion}
                for rp in rol.permisos
            ],
        }
        for rol in roles
    ]


@router.get("/permissions-matrix")
def matriz_permisos(
    _: Usuario = Depends(require_admin), db: Session = Depends(get_db)
):
    roles = db.scalars(select(Rol).order_by(Rol.id_rol)).all()
    permisos = db.scalars(select(Permiso).order_by(Permiso.modulo, Permiso.accion)).all()
    asignaciones = db.scalars(select(RolPermiso)).all()
    mapa = {(rp.id_rol, rp.id_permiso) for rp in asignaciones}
    return {
        "roles": [{"id_rol": r.id_rol, "nombre": r.nombre} for r in roles],
        "modulos": sorted({p.modulo for p in permisos}),
        "acciones": sorted({p.accion for p in permisos}),
        "matriz": [
            {
                "id_permiso": p.id_permiso,
                "modulo": p.modulo,
                "accion": p.accion,
                "roles": [
                    r.nombre for r in roles if (r.id_rol, p.id_permiso) in mapa
                ],
            }
            for p in permisos
        ],
    }


@router.get("/students")
def listar_estudiantes(
    _: Usuario = Depends(require_roles(*DIRECTORY_ROLES)), db: Session = Depends(get_db)
):
    estudiantes = db.scalars(
        select(Estudiante).options(
            selectinload(Estudiante.usuario).selectinload(Usuario.sede),
            selectinload(Estudiante.carrera),
            selectinload(Estudiante.plan),
        ).order_by(Estudiante.codigo)
    ).all()
    return [student_out(estudiante) for estudiante in estudiantes]


@router.get("/professors")
def listar_profesores(
    _: Usuario = Depends(require_roles(*DIRECTORY_ROLES)), db: Session = Depends(get_db)
):
    profesores = db.scalars(
        select(Profesor).options(
            selectinload(Profesor.usuario).selectinload(Usuario.sede),
            selectinload(Profesor.titulos),
        ).order_by(Profesor.id_profesor)
    ).all()
    return [professor_out(profesor) for profesor in profesores]


@router.get("/{id_usuario}")
def obtener_usuario(
    id_usuario: int,
    _: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    usuario = db.scalar(
        select(Usuario)
        .where(Usuario.id_usuario == id_usuario)
        .options(selectinload(Usuario.rol), selectinload(Usuario.sede))
    )
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return user_out(usuario)


@router.post("", status_code=status.HTTP_201_CREATED)
def crear_usuario(
    payload: UsuarioCreate,
    request: Request,
    usuario_actual: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if usuario_actual.rol.nombre != "admin" and payload.id_rol != 0:
        pass

    existente = db.scalar(
        select(Usuario).where(
            (func.lower(Usuario.email) == payload.email.lower())
            | (Usuario.cedula == payload.cedula)
        )
    )
    if existente:
        raise HTTPException(status_code=409, detail="Correo o cédula ya registrados.")

    rol = db.get(Rol, payload.id_rol)
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado.")
    if rol.nombre in {"admin"} and usuario_actual.rol.nombre != "admin":
        raise HTTPException(status_code=403, detail="Solo el administrador general puede crear administradores.")

    nuevo = Usuario(
        id_rol=rol.id_rol,
        id_sede=payload.id_sede,
        nombre=payload.nombre.strip(),
        email=payload.email.lower(),
        cedula=payload.cedula.strip(),
        password_hash=hash_password(payload.password),
        telefono=payload.telefono,
        activo=True,
    )
    db.add(nuevo)
    db.flush()

    if rol.nombre == "estudiante":
        carrera = db.get(Carrera, payload.id_carrera) if payload.id_carrera else db.scalar(select(Carrera))
        if not carrera:
            raise HTTPException(status_code=400, detail="Debe indicar una carrera para el estudiante.")
        plan = db.get(PlanEstudio, payload.id_plan) if payload.id_plan else db.scalar(
            select(PlanEstudio).where(PlanEstudio.id_carrera == carrera.id_carrera)
        )
        db.add(
            Estudiante(
                id_usuario=nuevo.id_usuario,
                id_carrera=carrera.id_carrera,
                id_plan=plan.id_plan if plan else None,
                codigo=payload.codigo or f"EST-{datetime.now().year}-{nuevo.id_usuario:04d}",
                anio_ingreso=payload.anio_ingreso or datetime.now().year,
            )
        )
    elif rol.nombre == "profesor":
        db.add(
            Profesor(
                id_usuario=nuevo.id_usuario,
                id_sede=payload.id_sede,
                categoria=payload.categoria or "docente",
                dedicacion=payload.dedicacion or "tiempo completo",
            )
        )

    registrar_auditoria(
        db,
        usuario_actual,
        "CREAR",
        "usuario",
        nuevo.id_usuario,
        f"Usuario {nuevo.email} con rol {rol.nombre}",
        get_client_ip(request),
    )
    db.commit()
    db.refresh(nuevo)
    return user_out(nuevo)


@router.patch("/{id_usuario}/status")
def cambiar_estado_usuario(
    id_usuario: int,
    payload: UsuarioStatusUpdate,
    request: Request,
    usuario_actual: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    usuario = db.scalar(
        select(Usuario)
        .where(Usuario.id_usuario == id_usuario)
        .options(selectinload(Usuario.rol), selectinload(Usuario.sede))
    )
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    if usuario.id_usuario == usuario_actual.id_usuario:
        raise HTTPException(status_code=400, detail="No puede desactivar su propia cuenta.")
    if usuario.rol.nombre == "admin" and usuario_actual.rol.nombre != "admin":
        raise HTTPException(status_code=403, detail="No puede modificar un administrador.")
    usuario.activo = payload.activo
    registrar_auditoria(
        db,
        usuario_actual,
        "ACTUALIZAR",
        "usuario",
        usuario.id_usuario,
        f"Estado activo={payload.activo}",
        get_client_ip(request),
    )
    db.commit()
    return user_out(usuario)
