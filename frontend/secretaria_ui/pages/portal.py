"""Portal principal con navegación por secciones y roles."""
from __future__ import annotations

from nicegui import ui

from ..api_client import ApiError
from ..layout import ADMIN_NAV, STUDENT_NAV, build_shell
from ..session import ADMIN_ROLES, clear_session, guard
from ..theme import apply_theme
from .admin import ADMIN_RENDERERS
from .student import STUDENT_RENDERERS


@ui.page("/app/{section}")
async def portal_page(section: str) -> None:
    apply_theme()
    user = guard()
    if not user:
        return

    role = user.get("rol", "estudiante")
    if role in ADMIN_ROLES:
        allowed = {key for group in ADMIN_NAV for key, _, _ in group["items"]}
        renderers = ADMIN_RENDERERS
    elif role == "estudiante":
        allowed = {key for group in STUDENT_NAV for key, _, _ in group["items"]}
        renderers = STUDENT_RENDERERS
    else:
        allowed = {"dashboard", "grades", "courses"}
        renderers = ADMIN_RENDERERS

    if section not in allowed:
        ui.navigate.to("/app/dashboard")
        return

    content = build_shell(user, section)
    with content:
        try:
            renderer = renderers.get(section)
            if not renderer:
                ui.navigate.to("/app/dashboard")
                return
            await renderer(user)
        except ApiError as exc:
            if exc.status_code == 401:
                clear_session()
                ui.notify("La sesión expiró. Inicie sesión nuevamente.", type="warning")
                ui.navigate.to("/login")
                return
            if exc.status_code == 403:
                ui.html(
                    '<div class="alert danger">No tiene permisos para acceder a esta '
                    f"sección.<br><small>{exc.detail}</small></div>"
                )
                return
            ui.html(f'<div class="alert danger">{exc.detail}</div>')
