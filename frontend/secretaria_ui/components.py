"""Componentes reutilizables de la interfaz."""
from __future__ import annotations

import html
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any, Iterable, Iterator

from nicegui import ui


class Raw:
    def __init__(self, value: str):
        self.value = value


def raw(value: str) -> Raw:
    return Raw(value)


def esc(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Sí" if value else "No"
    return html.escape(str(value))


def _cell(value: Any) -> str:
    if isinstance(value, Raw):
        return value.value
    return esc(value)


def fmt_date(value: Any, with_time: bool = False) -> str:
    if not value:
        return "—"
    if isinstance(value, (datetime, date)):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return str(value)
    if isinstance(dt, datetime):
        return dt.strftime("%d/%m/%Y %H:%M" if with_time else "%d/%m/%Y")
    return dt.strftime("%d/%m/%Y")


def fmt_money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "—"


def tone_for(value: Any) -> str:
    text = str(value or "").lower()
    if text in {
        "online",
        "pagado",
        "confirmada",
        "confirmado",
        "activo",
        "commit",
        "aprobado",
        "abierto",
        "conectado",
        "activa",
        "paz y salvo",
        "inscrito",
        "true",
        "sí",
    }:
        return "green"
    if text in {
        "offline",
        "anulada",
        "anulado",
        "rollback",
        "cerrado",
        "retirado",
        "suspendido",
        "degradado",
        "pago pendiente",
        "false",
        "no",
    }:
        return "red"
    if text in {"pendiente", "prepare", "planificado", "warning", "por confirmar"}:
        return "yellow"
    return "blue"


def badge_html(text: Any, tone: str | None = None) -> str:
    return f'<span class="badge {tone or tone_for(text)}">{esc(text)}</span>'


def badge(text: Any, tone: str | None = None) -> None:
    ui.html(badge_html(text, tone))


def page_intro(text: str) -> None:
    with ui.element("div").classes("page-intro"):
        ui.html(f"<p>{esc(text)}</p>")


@contextmanager
def grid(classes: str = "grid-2") -> Iterator[Any]:
    with ui.element("div").classes(classes) as container:
        yield container


@contextmanager
def card(
    title: str | None = None,
    subtitle: str | None = None,
    badge_text: str | None = None,
    badge_tone: str | None = None,
    classes: str = "",
) -> Iterator[Any]:
    with ui.element("section").classes(f"card {classes}".strip()) as box:
        if title:
            with ui.element("div").classes("card-header"):
                with ui.element("div"):
                    ui.html(f"<h2>{esc(title)}</h2>")
                    if subtitle:
                        ui.html(f"<small>{esc(subtitle)}</small>")
                if badge_text:
                    badge(badge_text, badge_tone)
        yield box


def kpis(items: Iterable[tuple[Any, Any, Any]]) -> None:
    with ui.element("div").classes("kpi-grid"):
        for label, value, meta in items:
            with ui.element("article").classes("card kpi"):
                ui.label(label).classes("kpi-label")
                ui.label(str(value)).classes("kpi-value")
                ui.label(meta or "").classes("kpi-meta")


def stat_line(label: str, value: Any, tone: str | None = None) -> None:
    with ui.element("div").classes("stat-line"):
        ui.label(label)
        if tone:
            ui.html(badge_html(value, tone))
        else:
            ui.label(str(value))


def empty(text: str = "No hay información disponible.") -> None:
    ui.html(f'<div class="empty">{esc(text)}</div>')


def alert(text: str, kind: str = "warning") -> None:
    ui.html(f'<div class="alert {kind}">{esc(text)}</div>')


SIM_NOTICE_TEXT = (
    "Vista de simulación académica: la arquitectura distribuida "
    "(2PC, replicación y fragmentación) se modela lógicamente sobre una "
    "única base de datos PostgreSQL."
)


def sim_badge() -> None:
    ui.html('<span class="badge yellow">SIMULACIÓN</span>')


def sim_notice(text: str | None = None) -> None:
    alert(text or SIM_NOTICE_TEXT, "warning")


def table(
    headers: list[str],
    rows: list[list[Any]],
    *,
    empty_text: str = "No hay registros.",
) -> None:
    if not rows:
        empty(empty_text)
        return
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{_cell(cell)}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    ui.html(
        f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
    )


def timeline(items: Iterable[tuple[str, str]]) -> None:
    rows = "".join(
        f'<div class="timeline-item"><span class="timeline-time">{esc(t)}</span>'
        f'<span class="timeline-text">{v if isinstance(v, Raw) else esc(v)}</span></div>'
        for t, v in items
    )
    ui.html(f'<div class="timeline">{rows}</div>')


def progress(value: float) -> None:
    pct = max(0.0, min(100.0, float(value)))
    ui.html(
        f'<div class="progress"><span style="width:{pct:.1f}%"></span></div>'
    )


def options(items: Iterable[dict], label_key: str, value_key: str) -> dict:
    return {item[value_key]: item[label_key] for item in items}


def entity_row(title: str, subtitle: str, actions: list[tuple[str, Any, str]] | None = None) -> None:
    with ui.element("div").classes("entity-row"):
        with ui.element("div").classes("entity-main"):
            ui.html(f"<strong>{esc(title)}</strong>")
            ui.html(f"<small>{esc(subtitle)}</small>")
        if actions:
            with ui.element("div").classes("mini-actions"):
                for label, handler, style in actions:
                    ui.button(label, on_click=handler).classes(f"mini-btn {style}".strip()).props(
                        "flat no-caps dense"
                    )
