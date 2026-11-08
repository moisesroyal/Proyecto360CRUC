"""Dependencias compartidas de la API."""
from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import decode_access_token
from ..models import Usuario

bearer_scheme = HTTPBearer(auto_error=False)

ADMIN_ROLES = {"admin", "admin_facultad", "coordinador", "secretaria"}
SUPERADMIN_ROLES = {"admin"}
STAFF_ROLES = ADMIN_ROLES | {"profesor"}


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "desconocida"


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso requerido.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")
    usuario = db.get(Usuario, user_id)
    if not usuario or not usuario.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo.")
    return usuario


def require_roles(*roles: str) -> Callable[..., Usuario]:
    allowed = {rol.lower() for rol in roles}

    def dependency(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.rol.nombre.lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para realizar esta operación.",
            )
        return usuario

    return dependency


require_admin = require_roles(*ADMIN_ROLES)
require_superadmin = require_roles(*SUPERADMIN_ROLES)
require_staff = require_roles(*STAFF_ROLES)
