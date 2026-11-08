"""Estructura visual compartida (sidebar, topbar y contenido)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from nicegui import ui

from .session import clear_session

ROLE_LABELS = {
    "admin": "Administrador general",
    "admin_facultad": "Administrador de facultad",
    "coordinador": "Coordinador académico",
    "secretaria": "Secretaría académica",
    "profesor": "Profesor",
    "estudiante": "Estudiante",
}

SECTION_TITLES = {
    "dashboard": "Dashboard",
    "infrastructure": "Estado de nodos (simulación)",
    "replication": "Red y replicación (simulación)",
    "architecture": "Arquitectura y diccionario",
    "data": "Distribución de datos (simulación)",
    "fragmentation": "Fragmentación (simulación)",
    "transactions": "Monitor 2PC (simulación)",
    "concurrency": "Concurrencia y bloqueos (simulación)",
    "queries": "Consultas globales y JOINs (simulación)",
    "recovery": "Logs y fallos (simulación)",
    "users": "Usuarios y permisos",
    "academic": "Estructura académica",
    "periods": "Períodos académicos",
    "groups": "Grupos y horarios",
    "enrollments": "Matrículas",
    "grades": "Calificaciones",
    "payments": "Pagos",
    "audit": "Auditoría",
    "enrollment": "Mi matrícula",
    "courses": "Mis asignaturas",
    "profile": "Mi perfil",
}

ADMIN_NAV = [
    {
        "title": None,
        "items": [("dashboard", "⌂", "Dashboard")],
    },
    {
        "title": "▣ Infraestructura",
        "items": [
            ("infrastructure", "◉", "Estado de nodos (sim)"),
            ("replication", "⇄", "Red y replicación (sim)"),
            ("architecture", "▤", "Arquitectura y diccionario"),
        ],
    },
    {
        "title": "▤ Datos distribuidos",
        "items": [
            ("data", "◫", "Distribución de datos (sim)"),
            ("fragmentation", "◧", "Fragmentación (sim)"),
        ],
    },
    {
        "title": "↻ Transacciones",
        "items": [
            ("transactions", "⇋", "Monitor 2PC (sim)"),
            ("concurrency", "⚿", "Concurrencia y bloqueos (sim)"),
        ],
    },
    {
        "title": "⌕ Consultas",
        "items": [("queries", "⌕", "Consultas globales (sim)")],
    },
    {
        "title": "⚠ Recuperación",
        "items": [("recovery", "⚠", "Logs y fallos (sim)")],
    },
    {
        "title": "⚙ Administración",
        "items": [
            ("users", "♟", "Usuarios y permisos"),
            ("academic", "▦", "Estructura académica"),
            ("periods", "▣", "Períodos"),
            ("groups", "▤", "Grupos y horarios"),
            ("enrollments", "✎", "Matrículas"),
            ("grades", "✓", "Calificaciones"),
            ("payments", "$", "Pagos"),
            ("audit", "◎", "Auditoría"),
        ],
    },
]

STUDENT_NAV = [
    {
        "title": None,
        "items": [
            ("dashboard", "⌂", "Dashboard"),
            ("enrollment", "✎", "Mi matrícula"),
            ("courses", "▤", "Mis asignaturas"),
            ("grades", "✓", "Calificaciones"),
            ("payments", "$", "Pagos"),
            ("profile", "◎", "Mi perfil"),
        ],
    }
]


async def _logout() -> None:
    clear_session()
    ui.navigate.to("/login")


def _nav_link(section: str, icon: str, label: str, active: str) -> None:
    classes = "nav-item" + (" active" if section == active else "")
    ui.button(
        f"{icon}  {label}",
        on_click=lambda s=section: ui.navigate.to(f"/app/{s}"),
    ).classes(classes).props("flat no-caps align=left")


def build_shell(user: dict, section: str) -> Any:
    role = user.get("rol", "estudiante")
    is_staff = role != "estudiante"
    nav = ADMIN_NAV if is_staff else STUDENT_NAV
    title = SECTION_TITLES.get(section, "Portal")
    ui.page_title(f"{title} · Universidad Distribuida 360°")

    with ui.element("div").classes("app-shell"):
        with ui.element("aside").classes("sidebar"):
            with ui.element("div").classes("brand"):
                ui.html('<div class="brand-icon">🎓</div>')
                with ui.element("div"):
                    ui.html("<strong>Universidad<br>Distribuida 360°</strong>")
                    ui.html("<small>Base de Datos Distribuida</small>")

            with ui.element("nav"):
                for group in nav:
                    with ui.element("div").classes("nav-group"):
                        if group["title"]:
                            ui.html(f'<div class="nav-title">{group["title"]}</div>')
                        for item_section, icon, label in group["items"]:
                            _nav_link(item_section, icon, label, section)

            with ui.element("div").classes("sidebar-footer"):
                ui.html('<span class="online-dot"></span> Sistema en línea (Local)')

        with ui.element("main").classes("main"):
            with ui.element("header").classes("topbar"):
                with ui.element("div"):
                    ui.html('<span class="breadcrumb">Universidad Distribuida 360°</span>')
                    ui.html(f"<h1>{title}</h1>")
                with ui.element("div").classes("user-area"):
                    clock = ui.label("").classes("clock")
                    ui.timer(
                        1.0,
                        lambda: clock.set_text(datetime.now().strftime("%d/%m/%Y %H:%M")),
                    )
                    ui.html(f'<div class="avatar">{user.get("nombre", "?")[:1].upper()}</div>')
                    with ui.element("div"):
                        ui.html(f'<strong>{user.get("nombre", "")}</strong>')
                        ui.html(f'<small>{ROLE_LABELS.get(role, role)}</small>')
                    ui.button("Salir", on_click=_logout, color="white").classes(
                        "logout-btn"
                    ).props("flat no-caps dense")
            content = ui.element("div").classes("content")
    return content
