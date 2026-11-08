"""Secciones del portal del estudiante."""
from __future__ import annotations

from functools import partial

from nicegui import ui

from ..api_client import ApiError
from ..components import (
    alert,
    badge,
    badge_html,
    card,
    empty,
    entity_row,
    fmt_date,
    fmt_money,
    grid,
    kpis,
    page_intro,
    raw,
    stat_line,
    table,
    tone_for,
)
from ..session import api


def _horario_text(item: dict) -> str:
    return (
        f"{item['dia']} {item['inicio']}-{item['fin']} · {item['aula']}"
    )


async def render_student_dashboard(user: dict) -> None:
    data = await api().get("/dashboard/student")
    estudiante = data["estudiante"]
    periodo = data.get("periodo") or {}
    matricula = data.get("matricula")
    resumen = data["resumen"]
    page_intro(
        f"Bienvenido(a), {estudiante['nombre']}. Este es el resumen de tu actividad "
        f"académica en {estudiante['carrera']}."
    )
    kpis(
        [
            ("Créditos inscritos", resumen["creditos"], f"Máximo {periodo.get('max_creditos', '—')}"),
            ("Asignaturas", resumen["asignaturas"], "Matriculadas"),
            ("Índice académico", resumen["indice"], "Escala 0 a 3"),
            ("Estado financiero", resumen["estado_financiero"], "Matrícula actual"),
        ]
    )

    if matricula and matricula["estado"] == "pendiente":
        alert(
            "Tu matrícula está pendiente de confirmación. Realiza el pago para "
            "confirmarla y asegurar tus cupos.",
            "warning",
        )
    if resumen["estado_financiero"].lower().startswith("pago pendiente"):
        alert("Tienes un pago pendiente asociado a tu matrícula actual.", "danger")

    with grid("grid-2"):
        with card("Período y matrícula", "Información vigente"):
            stat_line("Período", periodo.get("nombre", "—"))
            stat_line("Matrícula", f"#{matricula['id_matricula']}" if matricula else "Sin matrícula")
            stat_line("Estado", matricula["estado"] if matricula else "—", tone_for(matricula["estado"]) if matricula else None)
            stat_line("Fecha", fmt_date(matricula["fecha"]) if matricula else "—")
            stat_line("Créditos", matricula["total_creditos"] if matricula else 0)
            stat_line("Matrícula abierta", bool(periodo.get("matricula_abierta")), "green" if periodo.get("matricula_abierta") else "red")
        with card("Mi carrera", "Datos académicos"):
            stat_line("Carrera", estudiante["carrera"])
            stat_line("Plan", estudiante.get("plan") or "—")
            stat_line("Código", estudiante["codigo"])
            stat_line("Año de ingreso", estudiante["anio_ingreso"])
            stat_line("Estado", estudiante["estado"], tone_for(estudiante["estado"]))
            stat_line("Correo", estudiante["email"])

    with grid("grid-2"):
        with card("Horario semanal", "Clases del período actual"):
            table(
                ["Día", "Hora", "Materia", "Grupo", "Aula"],
                [
                    [h["dia"], f"{h['inicio']}-{h['fin']}", f"{h['codigo']} · {h['materia']}", h["grupo"], h["aula"]]
                    for h in data.get("horarios", [])
                ],
                empty_text="No tienes horarios registrados.",
            )
        with card("Asignaturas inscritas", "Carga académica actual"):
            table(
                ["Código", "Materia", "Créditos", "Profesor", "Estado"],
                [
                    [
                        a["codigo_materia"],
                        a["materia"],
                        a["creditos"],
                        a.get("profesor") or "—",
                        raw(badge_html(a.get("estado_detalle") or "inscrito")),
                    ]
                    for a in data.get("asignaturas", [])
                ],
                empty_text="No tienes asignaturas inscritas.",
            )

    with grid("grid-2"):
        with card("Calificaciones recientes", "Últimas evaluaciones"):
            table(
                ["Materia", "Evaluación", "Nota", "Ponderación", "Fecha"],
                [
                    [
                        f"{c['codigo']} · {c['materia']}",
                        c["evaluacion"],
                        c["nota"],
                        f"{c['ponderacion']}%",
                        fmt_date(c["fecha"]),
                    ]
                    for c in data.get("calificaciones", [])
                ],
                empty_text="Aún no tienes calificaciones registradas.",
            )
        with card("Pagos", "Estado financiero"):
            table(
                ["Monto", "Estado", "Método", "Referencia", "Fecha"],
                [
                    [
                        fmt_money(p["monto"]),
                        raw(badge_html(p["estado"])),
                        p.get("metodo") or "—",
                        p.get("referencia") or "—",
                        fmt_date(p["fecha"]),
                    ]
                    for p in data.get("pagos", [])
                ],
                empty_text="No hay pagos registrados.",
            )


async def render_student_enrollment(user: dict) -> None:
    client = api()
    data = await client.get("/dashboard/student")
    ofertas = await client.get("/academic/ofertas")
    periodo = data.get("periodo") or {}
    matricula = data.get("matricula")

    page_intro(
        "Selecciona las asignaturas disponibles para el período vigente. El sistema "
        "valida cupos, prerrequisitos, choques de horario y límite de créditos."
    )

    total_credits = matricula["total_creditos"] if matricula else 0
    max_credits = periodo.get("max_creditos", 24)
    kpis(
        [
            ("Créditos inscritos", total_credits, f"Límite {max_credits}"),
            ("Créditos disponibles", max(0, max_credits - total_credits), "Para nuevas asignaturas"),
            ("Oferta disponible", sum(1 for o in ofertas if o["puede_matricular"]), "Grupos habilitados"),
            ("Período", periodo.get("nombre", "—"), "Matrícula " + ("abierta" if periodo.get("matricula_abierta") else "cerrada")),
        ]
    )

    if not periodo.get("matricula_abierta"):
        alert("La ventana de matrícula está cerrada. No es posible inscribir nuevas asignaturas.", "danger")
    elif matricula and matricula["estado"] == "confirmada":
        alert(
            "Tu matrícula ya está confirmada. Para cambios contacta a la Secretaría Académica.",
            "warning",
        )
    elif matricula and matricula["estado"] == "pendiente":
        alert(
            "Tu matrícula está pendiente. Puedes seguir agregando asignaturas y luego "
            "confirmarla con el pago.",
            "warning",
        )

    async def enroll(id_grupo: int) -> None:
        try:
            response = await client.post(
                "/enrollments",
                {"periodo_id": int(periodo["id_periodo"]), "grupos": [id_grupo]},
            )
            ui.notify(response.get("mensaje", "Matrícula registrada."), type="positive")
            ui.navigate.to("/app/enrollment")
        except ApiError as exc:
            ui.notify(exc.detail, type="negative")

    async def withdraw(id_detalle: int) -> None:
        try:
            await client.delete(f"/enrollments/detalles/{id_detalle}")
            ui.notify("Asignatura retirada.", type="positive")
            ui.navigate.to("/app/enrollment")
        except ApiError as exc:
            ui.notify(exc.detail, type="negative")

    with card(
        "Mi matrícula actual",
        f"{periodo.get('nombre', '—')} · {total_credits} créditos",
        matricula["estado"] if matricula else "Sin matrícula",
        tone_for(matricula["estado"]) if matricula else "blue",
    ):
        table(
            ["Grupo", "Materia", "Créditos", "Profesor", "Horario", "Estado", ""],
            [
                [
                    a["codigo"],
                    f"{a['codigo_materia']} · {a['materia']}",
                    a["creditos"],
                    a.get("profesor") or "—",
                    ", ".join(
                        f"{h['dia_semana']} {h['hora_inicio']}-{h['hora_fin']}"
                        for h in a.get("horarios", [])
                    )
                    or "—",
                    raw(badge_html(a.get("estado_detalle") or "inscrito")),
                    raw(
                        '<span style="color:var(--muted);font-size:11px">'
                        "Retira desde la lista de acciones</span>"
                    ),
                ]
                for a in data.get("asignaturas", [])
            ],
            empty_text="Aún no tienes asignaturas inscritas.",
        )
        if matricula and matricula["estado"] == "pendiente" and data.get("asignaturas"):
            ui.html("<div style='height:8px'></div>")
            for asignatura in data["asignaturas"]:
                entity_row(
                    f"{asignatura['codigo_materia']} · {asignatura['materia']}",
                    f"{asignatura['codigo']} · {asignatura['creditos']} créditos",
                    [("Retirar", partial(withdraw, asignatura["id_detalle"]), "danger")],
                )

    with card("Oferta del período", "Grupos disponibles"):
        for oferta in ofertas:
            horario = ", ".join(
                f"{h['dia_semana']} {h['hora_inicio']}-{h['hora_fin']}"
                for h in oferta.get("horarios", [])
            ) or "Sin horario"
            estado = oferta.get("motivo") or "Disponible para matrícula"
            actions = []
            if oferta["puede_matricular"] and periodo.get("matricula_abierta"):
                actions.append(("Matricular", partial(enroll, oferta["id_grupo"]), "ok"))
            entity_row(
                f"{oferta['codigo']} · {oferta['materia']}",
                f"{oferta['creditos']} créditos · {oferta.get('profesor') or 'Sin docente'} · "
                f"{horario} · cupos {oferta['cupos_disponibles']}/{oferta['cupo']} · {estado}",
                actions,
            )


async def render_student_courses(user: dict) -> None:
    client = api()
    data = await client.get("/dashboard/student")
    matriculas = await client.get("/enrollments/me")
    page_intro(
        "Consulta las asignaturas de tu matrícula actual y el historial de matrículas "
        "de períodos anteriores."
    )
    kpis(
        [
            ("Asignaturas actuales", len(data.get("asignaturas", [])), "Período vigente"),
            ("Créditos", data["resumen"]["creditos"], "Carga actual"),
            ("Períodos cursados", len(matriculas), "Historial"),
            ("Índice académico", data["resumen"]["indice"], "Acumulado"),
        ]
    )
    with card("Asignaturas actuales", "Detalle de la matrícula vigente"):
        table(
            ["Código", "Materia", "Grupo", "Créditos", "Profesor", "Sede", "Horarios"],
            [
                [
                    a["codigo_materia"],
                    a["materia"],
                    a["codigo"],
                    a["creditos"],
                    a.get("profesor") or "—",
                    a.get("sede") or "—",
                    ", ".join(
                        f"{h['dia_semana']} {h['hora_inicio']}-{h['hora_fin']} · {h['aula']}"
                        for h in a.get("horarios", [])
                    )
                    or "—",
                ]
                for a in data.get("asignaturas", [])
            ],
        )
    with card("Historial de matrículas", "Períodos anteriores y actuales"):
        for matricula in matriculas:
            with ui.element("div").style("margin-bottom:18px"):
                with ui.element("div").classes("card-header"):
                    ui.html(
                        f"<h3>{esc_html(matricula['periodo']['nombre'])} · "
                        f"{matricula['total_creditos']} créditos</h3>"
                    )
                    badge(matricula["estado"])
                table(
                    ["Grupo", "Materia", "Créditos", "Nota final", "Estado"],
                    [
                        [
                            d["grupo"]["codigo"],
                            f"{d['grupo']['codigo_materia']} · {d['grupo']['materia']}",
                            d["grupo"]["creditos"],
                            d.get("nota_final") if d.get("nota_final") is not None else "—",
                            raw(badge_html(d["estado"])),
                        ]
                        for d in matricula.get("detalles", [])
                    ],
                    empty_text="Sin asignaturas.",
                )


def esc_html(value: str) -> str:
    import html

    return html.escape(str(value))


async def render_student_grades(user: dict) -> None:
    client = api()
    data = await client.get("/dashboard/student")
    calificaciones = await client.get("/enrollments/me/calificaciones")
    page_intro(
        "Consulta tus calificaciones por asignatura y evaluación. La nota final se "
        "calcula con las ponderaciones registradas por el docente."
    )
    notas = [c["nota"] for c in calificaciones]
    promedio = round(sum(notas) / len(notas), 1) if notas else 0
    kpis(
        [
            ("Calificaciones", len(calificaciones), "Evaluaciones registradas"),
            ("Promedio", promedio, "Sobre 100 puntos"),
            ("Índice académico", data["resumen"]["indice"], "Escala 0 a 3"),
            ("Asignaturas actuales", len(data.get("asignaturas", [])), "Período vigente"),
        ]
    )
    with card("Calificaciones registradas", "Historial de evaluaciones"):
        table(
            ["Materia", "Evaluación", "Nota", "Ponderación", "Fecha"],
            [
                [
                    f"{c['codigo']} · {c['materia']}",
                    c["evaluacion"],
                    c["nota"],
                    f"{c['ponderacion']}%",
                    fmt_date(c["fecha"]),
                ]
                for c in calificaciones
            ],
            empty_text="Aún no tienes calificaciones registradas.",
        )
    with card("Carga actual", "Notas pendientes"):
        table(
            ["Código", "Materia", "Créditos", "Nota final", "Profesor"],
            [
                [
                    a["codigo_materia"],
                    a["materia"],
                    a["creditos"],
                    a.get("nota_final") if a.get("nota_final") is not None else "Pendiente",
                    a.get("profesor") or "—",
                ]
                for a in data.get("asignaturas", [])
            ],
        )


async def render_student_payments(user: dict) -> None:
    client = api()
    pagos = await client.get("/payments/me")
    page_intro(
        "Consulta y regulariza los pagos asociados a tus matrículas. Al pagar una "
        "matrícula pendiente, esta se confirma automáticamente."
    )
    pendientes = [p for p in pagos if p["estado"] == "pendiente"]
    kpis(
        [
            ("Pagos", len(pagos), "Registrados"),
            ("Pendientes", len(pendientes), "Por regularizar"),
            ("Monto pendiente", fmt_money(sum(p["monto"] for p in pendientes)), "Total a pagar"),
            ("Pagados", sum(1 for p in pagos if p["estado"] == "pagado"), "Confirmados"),
        ]
    )
    if pendientes:
        alert(
            "Tienes pagos pendientes. Puedes simular el pago desde esta pantalla para "
            "confirmar tu matrícula.",
            "warning",
        )

    async def pay(pago: dict) -> None:
        try:
            await client.post(
                "/payments",
                {
                    "id_matricula": pago["id_matricula"],
                    "monto": pago["monto"],
                    "metodo": "tarjeta",
                    "referencia": f"PORTAL-{pago['id_pago']}",
                    "estado": "pagado",
                },
            )
            ui.notify("Pago registrado y matrícula confirmada.", type="positive")
            ui.navigate.to("/app/payments")
        except ApiError as exc:
            ui.notify(exc.detail, type="negative")

    with card("Pagos pendientes", "Regulariza tu matrícula"):
        if not pendientes:
            empty("No tienes pagos pendientes.")
        for pago in pendientes:
            entity_row(
                f"{fmt_money(pago['monto'])} · {pago['periodo']}",
                f"Referencia {pago.get('referencia') or '—'} · método {pago.get('metodo') or '—'}",
                [("Pagar ahora", partial(pay, pago), "ok")],
            )
    with card("Historial de pagos", "Todos los períodos"):
        table(
            ["Período", "Monto", "Estado", "Método", "Referencia", "Fecha"],
            [
                [
                    p["periodo"],
                    fmt_money(p["monto"]),
                    raw(badge_html(p["estado"])),
                    p.get("metodo") or "—",
                    p.get("referencia") or "—",
                    fmt_date(p["fecha"]),
                ]
                for p in pagos
            ],
        )


async def render_student_profile(user: dict) -> None:
    client = api()
    me = await client.get("/auth/me")
    data = await client.get("/dashboard/student")
    estudiante = data["estudiante"]
    page_intro("Datos personales y académicos registrados en la universidad.")
    with grid("grid-2"):
        with card("Datos personales", "Información de contacto"):
            stat_line("Nombre", me["nombre"])
            stat_line("Correo", me["email"])
            stat_line("Cédula", me["cedula"])
            stat_line("Rol", me["rol"])
            stat_line("Último acceso", fmt_date(me.get("ultimo_acceso"), with_time=True))
            stat_line("Estado", "Activo" if me["activo"] else "Inactivo", "green" if me["activo"] else "red")
        with card("Datos académicos", "Carrera y plan"):
            stat_line("Código", estudiante["codigo"])
            stat_line("Carrera", estudiante["carrera"])
            stat_line("Plan", estudiante.get("plan") or "—")
            stat_line("Año de ingreso", estudiante["anio_ingreso"])
            stat_line("Índice académico", estudiante["indice_academico"])
            stat_line("Estado", estudiante["estado"], tone_for(estudiante["estado"]))
    with card("Resumen del período", "Matrícula vigente"):
        resumen = data["resumen"]
        stat_line("Créditos", resumen["creditos"])
        stat_line("Asignaturas", resumen["asignaturas"])
        stat_line("Estado financiero", resumen["estado_financiero"], tone_for(resumen["estado_financiero"]))


STUDENT_RENDERERS = {
    "dashboard": render_student_dashboard,
    "enrollment": render_student_enrollment,
    "courses": render_student_courses,
    "grades": render_student_grades,
    "payments": render_student_payments,
    "profile": render_student_profile,
}
