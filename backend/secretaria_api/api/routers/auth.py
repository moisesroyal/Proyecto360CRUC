from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ...core.database import get_db
from ...core.security import create_access_token, hash_password, verify_password
from ...models import (
    Carrera,
    Estudiante,
    EstadoActivo,
    Permiso,
    PlanEstudio,
    Rol,
    RolPermiso,
    Usuario,
)
from ...schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from ...services.audit import registrar_auditoria, registrar_evento
from ..deps import get_client_ip, get_current_user
from ..serializers import user_session

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    identificador = payload.identifier.strip()
    usuario = db.scalar(
        select(Usuario)
        .where(
            or_(
                func.lower(Usuario.email) == identificador.lower(),
                Usuario.cedula == identificador,
                func.lower(Usuario.nombre) == identificador.lower(),
            )
        )
        .options(selectinload(Usuario.rol), selectinload(Usuario.estudiante), selectinload(Usuario.profesor))
    )
    if not usuario or not verify_password(payload.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas. Verifique sus datos.",
        )
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta está inactiva. Contacte a la Secretaría Académica.",
        )

    usuario.ultimo_acceso = datetime.now(timezone.utc)
    registrar_auditoria(
        db, usuario, "LOGIN", "usuario", usuario.id_usuario, "Inicio de sesión", get_client_ip(request)
    )
    db.commit()
    db.refresh(usuario)

    token = create_access_token(str(usuario.id_usuario), usuario.rol.nombre)
    return {"access_token": token, "token_type": "bearer", "user": user_session(usuario)}


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    existe = db.scalar(
        select(Usuario).where(
            or_(
                func.lower(Usuario.email) == payload.email.lower(),
                Usuario.cedula == payload.cedula,
            )
        )
    )
    if existe:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo o número de cédula ya se encuentran registrados.",
        )

    rol = db.scalar(select(Rol).where(Rol.nombre == "estudiante"))
    if not rol:
        raise HTTPException(status_code=500, detail="El rol de estudiante no está configurado.")

    carrera = None
    if payload.id_carrera:
        carrera = db.get(Carrera, payload.id_carrera)
        if not carrera:
            raise HTTPException(status_code=404, detail="La carrera seleccionada no existe.")
    else:
        carrera = db.scalar(select(Carrera).order_by(Carrera.id_carrera))

    plan = None
    if payload.id_plan:
        plan = db.get(PlanEstudio, payload.id_plan)
        if not plan:
            raise HTTPException(status_code=404, detail="El plan de estudio no existe.")
    elif carrera:
        plan = db.scalar(
            select(PlanEstudio).where(PlanEstudio.id_carrera == carrera.id_carrera)
        )

    usuario = Usuario(
        id_rol=rol.id_rol,
        nombre=payload.nombre.strip(),
        email=payload.email.lower(),
        cedula=payload.cedula.strip(),
        password_hash=hash_password(payload.password),
        telefono=payload.telefono,
        activo=True,
    )
    db.add(usuario)
    db.flush()

    if carrera:
        estudiante = Estudiante(
            id_usuario=usuario.id_usuario,
            id_carrera=carrera.id_carrera,
            id_plan=plan.id_plan if plan else None,
            codigo=f"EST-{datetime.now().year}-{usuario.id_usuario:04d}",
            estado=EstadoActivo.ACTIVO,
            anio_ingreso=datetime.now().year,
        )
        db.add(estudiante)

    registrar_auditoria(
        db,
        usuario,
        "CREAR",
        "usuario",
        usuario.id_usuario,
        "Registro de nuevo estudiante desde el portal",
        get_client_ip(request),
    )
    registrar_evento(db, f"Nuevo estudiante registrado: {usuario.email}", origen="auth")
    db.commit()

    usuario = db.scalar(
        select(Usuario)
        .where(Usuario.id_usuario == usuario.id_usuario)
        .options(selectinload(Usuario.rol), selectinload(Usuario.estudiante), selectinload(Usuario.profesor))
    )
    token = create_access_token(str(usuario.id_usuario), usuario.rol.nombre)
    return {"access_token": token, "token_type": "bearer", "user": user_session(usuario)}


@router.get("/me")
def me(usuario: Usuario = Depends(get_current_user)) -> dict:
    return user_session(usuario)


@router.get("/permissions")
def mis_permisos(
    usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    filas = db.execute(
        select(Permiso.modulo, Permiso.accion)
        .join(RolPermiso, RolPermiso.id_permiso == Permiso.id_permiso)
        .where(RolPermiso.id_rol == usuario.id_rol)
        .order_by(Permiso.modulo, Permiso.accion)
    ).all()
    return {
        "rol": usuario.rol.nombre,
        "permisos": [{"modulo": modulo, "accion": accion} for modulo, accion in filas],
    }
