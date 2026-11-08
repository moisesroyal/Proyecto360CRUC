"""Sesión del usuario en el frontend (cookie firmada de NiceGUI)."""
from __future__ import annotations

from nicegui import app, ui

from .api_client import ApiClient

ADMIN_ROLES = {"admin", "admin_facultad", "coordinador", "secretaria"}
SUPERADMIN_ROLES = {"admin"}


def set_session(token: str, user: dict) -> None:
    app.storage.user["token"] = token
    app.storage.user["user"] = user


def clear_session() -> None:
    app.storage.user.pop("token", None)
    app.storage.user.pop("user", None)


def get_token() -> str | None:
    return app.storage.user.get("token")


def get_user() -> dict | None:
    return app.storage.user.get("user")


def is_authenticated() -> bool:
    return bool(get_token() and get_user())


def is_admin(user: dict | None = None) -> bool:
    user = user or get_user() or {}
    return user.get("rol") in ADMIN_ROLES


def is_superadmin(user: dict | None = None) -> bool:
    user = user or get_user() or {}
    return user.get("rol") in SUPERADMIN_ROLES


def is_student(user: dict | None = None) -> bool:
    user = user or get_user() or {}
    return user.get("rol") == "estudiante"


def api() -> ApiClient:
    return ApiClient(get_token())


def redirect_to_login() -> None:
    ui.navigate.to("/login")


def guard() -> dict | None:
    user = get_user()
    if not get_token() or not user:
        redirect_to_login()
        return None
    return user
