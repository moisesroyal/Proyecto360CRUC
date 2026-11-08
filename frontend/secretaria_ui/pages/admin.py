"""Secciones del portal administrativo."""
from __future__ import annotations

import unicodedata
from datetime import date
from functools import partial
from typing import Any

from nicegui import ui

from ..api_client import ApiError
from ..components import (
    alert,
    badge,
    badge_html,
    card,
    empty,
    entity_row,
    esc,
    fmt_date,
    fmt_money,
    grid,
    kpis,
    options,
    page_intro,
    progress,
    raw,
    stat_line,
    table,
    timeline,
    tone_for,
)
from ..session import api

STATUS_TONES = {"online": "green", "offline": "red"}

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]


def _slug(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return value.lower()


def _dialog_card(title: str):
    dialog = ui.dialog()
    with dialog, ui.card().classes("card").style("min-width:420px;max-width:560px;width:100%"):
        ui.html(f"<h2>{esc(title)}</h2>")
        ui.separator().classes("q-my-sm")
        box = ui.column().classes("w-full gap-3")
    return dialog, box


def _field(label: str, **kwargs) -> ui.input:
    return ui.input(label, **kwargs).props("outlined dense").classes("w-full")


def _select(label: str, opts: dict, value: Any = None) -> ui.select:
    return (
        ui.select(opts, label=label, value=value)
        .props("outlined dense")
        .classes("w-full")
    )


def _map(nodes: list[dict]) -> None:
    positions = {"panama": "panama", "cocle": "cocle", "veraguas": "veraguas"}
    cards = []
    for node in nodes:
        slug = _slug(node["nombre"]).replace("á", "a").replace("é", "e")
        css = positions.get(slug, "cocle")
        tone = "green" if node["estado"] == "online" else "red"
        cards.append(
            f'<div class="node {css}"><div class="node-icon" style="color:var(--{tone})">◉</div>'
            f'<strong>{esc(node["nombre"])}</strong>'
            f'<small style="color:var(--{tone})">{esc(node["estado"])} · '
            f'{esc(node["latencia_ms"])} ms</small></div>'
        )
    links = '<div class="link l1"></div><div class="link l2"></div><div class="link l3"></div>'
    ui.html(f'<div class="map">{links}{"".join(cards)}</div>')


async def render_admin_dashboard(user: dict) -> None:
    data = await api().get("/dashboard/summary")
    k = data["kpis"]
    period = data.get("periodo") or {}
    page_intro(
        "Panorama general de la universidad distribuida: matrícula, nodos, "
        "replicación y actividad reciente."
    )
    kpis(
        [
            ("Estudiantes", k["estudiantes"], "Activos en el sistema"),
            ("Matrículas", k["matriculas"], f"{k['pagos_pendientes']} pago(s) pendiente(s)"),
            ("Nodos en línea", f"{k['nodos_online']}/{k['nodos_total']}", f"Latencia {k['latencia_promedio']} ms"),
            ("Oferta académica", k["grupos"], f"{k['materias']} materias · {k['carreras']} carreras"),
        ]
    )

    with grid("grid-2"):
        with card("Mapa de la red", "Nodos regionales y latencia", f"{k['nodos_online']}/{k['nodos_total']} en línea"):
            _map(data["nodos"])
        with card("Período académico", "Ventana de matrícula vigente"):
            if period:
                stat_line("Período", period["nombre"])
                stat_line("Estado", period["estado"], tone_for(period["estado"]))
                stat_line("Matrícula abierta", bool(period["matricula_abierta"]), "green" if period["matricula_abierta"] else "red")
                stat_line("Inicio", fmt_date(period["fecha_inicio"]))
                stat_line("Fin", fmt_date(period["fecha_fin"]))
            else:
                empty("No hay períodos registrados.")
            ui.html("<div style='height:14px'></div>")
            ui.html("<h3 style='font-size:13px;margin-bottom:8px'>Estudiantes por carrera</h3>")
            for item in data.get("carreras", []):
                with ui.element("div").classes("entity-row"):
                    ui.label(item["carrera"]).style("font-size:12px")
                    badge(item["estudiantes"], "blue")
            with ui.element("div").classes("entity-row"):
                ui.label("Profesores registrados").style("font-size:12px")
                badge(k["profesores"], "blue")

    with grid("grid-2"):
        with card("Matrículas recientes", "Últimos movimientos"):
            table(
                ["Estudiante", "Período", "Créditos", "Estado", "Fecha"],
                [
                    [
                        f"{m['estudiante']} ({m['codigo']})",
                        m["periodo"],
                        m["creditos"],
                        raw(badge_html(m["estado"])),
                        fmt_date(m["fecha"]),
                    ]
                    for m in data.get("matriculas_recientes", [])
                ],
                empty_text="Sin matrículas recientes.",
            )
        with card("Estado de nodos", "Disponibilidad y replicación"):
            for node in data["nodos"]:
                with ui.element("div").classes("entity-row"):
                    with ui.element("div").classes("entity-main"):
                        ui.html(f"<strong>{esc(node['nombre'])}</strong>")
                        ui.html(
                            f"<small>{esc(node['rol'])} · {esc(node['host'])}</small>"
                        )
                    with ui.element("div").style("min-width:120px;text-align:right"):
                        badge(node["estado"])
                        ui.label(f"{node['replicacion_pct']}%").style(
                            "font-size:11px;color:var(--muted)"
                        )
                        progress(node["replicacion_pct"])


async def render_infrastructure(user: dict) -> None:
    nodes = await api().get("/infrastructure/nodes")
    online = sum(1 for n in nodes if n["estado"] == "online")
    avg_latency = round(sum(n["latencia_ms"] for n in nodes) / len(nodes), 1) if nodes else 0
    avg_repl = round(sum(n["replicacion_pct"] for n in nodes) / len(nodes), 1) if nodes else 0
    page_intro(
        "Monitoreo de los nodos que componen la base de datos distribuida. "
        "Puede alternar la disponibilidad de cada nodo para simular fallos."
    )
    kpis(
        [
            ("Nodos en línea", f"{online}/{len(nodes)}", "Disponibilidad de la red"),
            ("Latencia promedio", f"{avg_latency} ms", "Entre sedes"),
            ("Replicación promedio", f"{avg_repl}%", "Sincronización de réplicas"),
            ("Nodos fuera de línea", len(nodes) - online, "Requieren atención"),
        ]
    )

    async def toggle_node(node_id: int) -> None:
        try:
            await api().post(f"/infrastructure/nodes/{node_id}/toggle")
            ui.notify("Estado del nodo actualizado.", type="positive")
            ui.navigate.to("/app/infrastructure")
        except ApiError as exc:
            ui.notify(exc.detail, type="negative")

    with grid("grid-2"):
        with card("Mapa de la red", "Latencia por nodo"):
            _map(nodes)
        with card("Acciones de infraestructura", "Simulación de fallos"):
            alert(
                "Al desconectar un nodo se detiene la replicación y los enlaces se "
                "marcan como degradados.",
                "warning",
            )
            for node in nodes:
                entity_row(
                    f"{node['nombre']} · {node['estado']}",
                    f"{node['host']} · {node['latencia_ms']} ms · réplica {node['replicacion_pct']}%",
                    [
                        (
                            "Conectar" if node["estado"] == "offline" else "Desconectar",
                            partial(toggle_node, node["id_nodo"]),
                            "ok" if node["estado"] == "offline" else "danger",
                        )
                    ],
                )

    with card("Detalle de nodos", "Información técnica"):
        table(
            ["Nodo", "Rol", "Host", "Estado", "Latencia", "Replicación", "Última sincronización"],
            [
                [
                    n["nombre"],
                    n["rol"],
                    n["host"],
                    raw(badge_html(n["estado"])),
                    f"{n['latencia_ms']} ms",
                    f"{n['replicacion_pct']}%",
                    fmt_date(n.get("ultima_sincronizacion"), with_time=True),
                ]
                for n in nodes
            ],
        )


async def render_replication(user: dict) -> None:
    data = await api().get("/infrastructure/replication")
    nodes = data["nodos"]
    links = data["enlaces"]
    page_intro(
        "Topología de replicación entre las sedes de Panamá, Coclé y Veraguas, "
        "con el estado de cada enlace de comunicación."
    )
    kpis(
        [
            ("Réplicas activas", sum(1 for n in nodes if n["estado"] == "online"), "Nodos operativos"),
            ("Enlaces", len(links), "Conexiones entre sedes"),
            ("Enlaces degradados", sum(1 for l in links if l["estado"] != "Conectado"), "Requieren revisión"),
            ("Replicación activa", "Sí" if data["replicacion_activa"] else "No", "Estado global"),
        ]
    )
    if not data["replicacion_activa"]:
        alert("La replicación está degradada. Verifique los nodos fuera de línea.", "danger")
    else:
        alert("Todos los nodos están en línea y la replicación se encuentra activa.", "success")

    with grid("grid-2"):
        with card("Enlaces de red", "Latencia y estado"):
            table(
                ["Origen", "Destino", "Latencia", "Estado"],
                [
                    [
                        link["origen"],
                        link["destino"],
                        f"{link['latencia_ms']} ms",
                        raw(badge_html(link["estado"])),
                    ]
                    for link in links
                ],
            )
        with card("Réplicas", "Sincronización por nodo"):
            for node in nodes:
                with ui.element("div").style("margin-bottom:14px"):
                    with ui.element("div").classes("entity-row").style("border-bottom:0;padding-bottom:4px"):
                        ui.label(node["nombre"]).style("font-size:13px;font-weight:700")
                        badge(node["estado"])
                    progress(node["replicacion_pct"])
                    ui.label(f"{node['replicacion_pct']}% sincronizado").style(
                        "font-size:11px;color:var(--muted)"
                    )
    with card("Estrategia de replicación", "Catálogo y matrícula"):
        alert(
            "Panamá mantiene el catálogo institucional y las sedes regionales replican "
            "la matrícula y las calificaciones. Cada operación de escritura se propaga "
            "a las réplicas mediante el protocolo de dos fases (2PC).",
            "warning",
        )


async def render_architecture(user: dict) -> None:
    dictionary = await api().get("/infrastructure/data-dictionary")
    total_columns = sum(len(t["columnas"]) for t in dictionary)
    total_fks = sum(
        1 for t in dictionary for c in t["columnas"] if c.get("fk")
    )
    page_intro(
        "Diccionario de datos generado desde el modelo SQLAlchemy. Describe tablas, "
        "claves primarias, claves foráneas y tipos de datos."
    )
    kpis(
        [
            ("Tablas", len(dictionary), "Entidades del modelo"),
            ("Columnas", total_columns, "Atributos documentados"),
            ("Claves foráneas", total_fks, "Relaciones entre tablas"),
            ("Motor", "PostgreSQL", "SQLAlchemy + Alembic"),
        ]
    )
    for entry in dictionary:
        with ui.expansion(
            f"{entry['tabla']} · {len(entry['columnas'])} columnas",
            value=entry["tabla"] in {"usuario", "estudiante", "matricula"},
        ).classes("card").style("margin-bottom:10px"):
            ui.html(
                f"<div style='margin-bottom:10px;color:var(--muted);font-size:11px'>"
                f"Clave primaria: <strong>{esc(', '.join(entry['pk'])) or '—'}</strong></div>"
            )
            table(
                ["Columna", "Tipo", "Nulable", "PK", "FK"],
                [
                    [
                        c["nombre"],
                        c["tipo"],
                        "Sí" if c["nulable"] else "No",
                        raw('<span class="badge blue">PK</span>') if c["pk"] else "—",
                        c.get("fk") or "—",
                    ]
                    for c in entry["columnas"]
                ],
            )


async def render_data(user: dict) -> None:
    data = await api().get("/infrastructure/fragmentation")
    page_intro(
        "Distribución de los datos entre sedes. La matrícula se fragmenta de forma "
        "horizontal y el catálogo académico se replica desde Panamá."
    )
    total_students = sum(f["estudiantes"] for f in data["fragmentos"])
    total_groups = sum(f["grupos"] for f in data["fragmentos"])
    kpis(
        [
            ("Fragmentos", len(data["fragmentos"]), "Particiones horizontales"),
            ("Estudiantes distribuidos", total_students, "Suma de fragmentos"),
            ("Grupos distribuidos", total_groups, "Oferta por sede"),
            ("Réplicas", len(data["replicas"]), "Copias del catálogo"),
        ]
    )
    with grid("grid-3"):
        for fragment in data["fragmentos"]:
            with card(
                fragment["sede"],
                fragment["fragmento"],
                f"{fragment['estudiantes']} estudiantes",
            ):
                stat_line("Estudiantes", fragment["estudiantes"])
                stat_line("Grupos", fragment["grupos"])
                stat_line("Estrategia", fragment["estrategia"])
    with grid("grid-2"):
        with card("Réplicas", "Copias mantenidas"):
            for replica in data["replicas"]:
                ui.html(f'<div class="alert success">{esc(replica)}</div>')
        with card("Estrategias de distribución", "Diseño de la base distribuida"):
            for strategy in data["estrategias"]:
                ui.html(
                    f'<div class="fragment-card"><strong>{esc(strategy["tipo"])}</strong>'
                    f'<p>{esc(strategy["descripcion"])}</p></div>'
                )


async def render_fragmentation(user: dict) -> None:
    data = await api().get("/infrastructure/fragmentation")
    page_intro(
        "Detalle de la fragmentación horizontal por sede y de las estrategias "
        "de distribución aplicadas al esquema académico."
    )
    with card("Fragmentos horizontales", "Estudiantes y grupos por sede"):
        table(
            ["Sede", "Fragmento", "Estudiantes", "Grupos", "Estrategia"],
            [
                [
                    f["sede"],
                    f["fragmento"],
                    f["estudiantes"],
                    f["grupos"],
                    f["estrategia"],
                ]
                for f in data["fragmentos"]
            ],
        )
    with grid("grid-3"):
        for strategy in data["estrategias"]:
            with card(strategy["tipo"], "Estrategia de distribución"):
                ui.html(f"<p style='color:var(--muted);font-size:12px;line-height:1.6'>{esc(strategy['descripcion'])}</p>")
    with card("Réplicas del catálogo", "Sincronización"):
        for replica in data["replicas"]:
            ui.html(f'<div class="alert success">{esc(replica)}</div>')
        alert(
            "La fragmentación permite que cada sede consulte localmente sus estudiantes "
            "y grupos, mientras las consultas globales integran los fragmentos.",
            "warning",
        )


async def render_transactions(user: dict) -> None:
    transactions = await api().get("/infrastructure/transactions")
    page_intro(
        "Monitor de transacciones distribuidas con el protocolo de confirmación de "
        "dos fases (2PC). Puede simular una transacción exitosa o un rollback."
    )
    kpis(
        [
            ("Transacciones", len(transactions), "Registradas en el monitor"),
            ("COMMIT", sum(1 for t in transactions if t["estado"] == "COMMIT"), "Confirmadas"),
            ("ROLLBACK", sum(1 for t in transactions if t["estado"] == "ROLLBACK"), "Revertidas"),
            ("En curso", sum(1 for t in transactions if t["estado"] == "PREPARE"), "Fase de preparación"),
        ]
    )

    async def simulate(tipo: str, nodes: int, rollback: bool) -> None:
        try:
            await api().post(
                "/infrastructure/transactions/simulate",
                {"tipo": tipo, "nodos": nodes, "forzar_rollback": rollback},
            )
            ui.notify("Transacción simulada correctamente.", type="positive")
            ui.navigate.to("/app/transactions")
        except ApiError as exc:
            ui.notify(exc.detail, type="negative")

    with grid("grid-2"):
        with card("Simular transacción 2PC", "Nueva operación distribuida"):
            tipo = _select("Tipo de transacción", {"Actualización": "Actualización", "Consulta": "Consulta", "Inserción": "Inserción"}, "Actualización")
            nodos = ui.number("Nodos involucrados", value=3, min=1, max=10).props("outlined dense").classes("w-full")
            rollback = ui.switch("Forzar ROLLBACK")
            ui.button(
                "Ejecutar simulación",
                on_click=lambda: simulate(tipo.value, int(nodos.value or 3), bool(rollback.value)),
            ).classes("primary-btn").props("no-caps unelevated")
        with card("Fases del protocolo", "Confirmación de dos fases"):
            timeline(
                [
                    ("Fase 1", "El coordinador envía PREPARE a todos los nodos."),
                    ("Fase 2", "Cada nodo confirma si puede ejecutar la operación."),
                    ("Decisión", "Si todos confirman, el coordinador envía COMMIT."),
                    ("Rollback", "Si un nodo falla, se envía ROLLBACK a todos."),
                ]
            )
            ui.html(
                '<div class="phase-flow"><div class="phase">PREPARE</div>'
                '<span class="arrow">→</span><div class="phase">COMMIT</div>'
                '<span class="arrow">→</span><div class="phase">FIN</div></div>'
            )

    with card("Historial de transacciones", "Últimos registros"):
        table(
            ["Código", "Tipo", "Nodos", "Estado", "Inicio", "Fin", "Detalle"],
            [
                [
                    t["codigo"],
                    t["tipo"],
                    t["nodos_involucrados"],
                    raw(badge_html(t["estado"])),
                    fmt_date(t["iniciada_en"], with_time=True),
                    fmt_date(t["finalizada_en"], with_time=True),
                    t.get("detalle") or "—",
                ]
                for t in transactions
            ],
        )


async def render_concurrency(user: dict) -> None:
    data = await api().get("/infrastructure/concurrency")
    page_intro(
        "Simulación de bloqueos y control de concurrencia sobre las operaciones de "
        "matrícula. Se aplican bloqueos compartidos para evitar condiciones de carrera."
    )
    kpis(
        [
            ("Registros bloqueados", data["registros_bloqueados"], "Detalles de matrícula activos"),
            ("Pasos", len(data["pasos"]), "Secuencia de bloqueo"),
            ("Interbloqueos", 0, "Detección automática"),
            ("Estado", "Sin conflictos", "Última simulación"),
        ]
    )
    with grid("grid-2"):
        with card("Secuencia de bloqueo", "Control de concurrencia"):
            timeline([(f"Paso {i + 1}", step) for i, step in enumerate(data["pasos"])])
        with card("Resultado", "Última simulación"):
            alert(data["mensaje"], "success")
            alert(
                "El bloqueo compartido se libera al confirmar o revertir la transacción. "
                "Las matrículas confirmadas no pueden modificarse.",
                "warning",
            )
            ui.button(
                "Volver a simular",
                on_click=lambda: ui.navigate.to("/app/concurrency"),
            ).classes("secondary-btn").props("no-caps")


async def render_queries(user: dict) -> None:
    page_intro(
        "Ejecute consultas SELECT/WITH sobre el esquema distribuido. Las consultas "
        "globales combinan fragmentos de estudiantes, matrículas y calificaciones."
    )
    with card("Editor SQL", "Solo se permiten consultas de lectura"):
        sql = ui.textarea(
            "Consulta",
            value=(
                "SELECT e.codigo, u.nombre, m.nombre AS materia, d.nota_final\n"
                "FROM estudiante e\n"
                "JOIN usuario u ON u.id_usuario = e.id_usuario\n"
                "JOIN matricula mt ON mt.id_estudiante = e.id_estudiante\n"
                "JOIN detalle_matricula d ON d.id_matricula = mt.id_matricula\n"
                "JOIN grupo g ON g.id_grupo = d.id_grupo\n"
                "JOIN materia m ON m.id_materia = g.id_materia\n"
                "ORDER BY u.nombre, m.nombre;"
            ),
        ).classes("sql-box").props("outlined")
        result = ui.column().classes("w-full")

        async def run_query() -> None:
            result.clear()
            try:
                data = await api().post("/infrastructure/query", {"sql": sql.value})
                with result:
                    ui.html(f'<div class="alert success">{esc(data["mensaje"])}</div>')
                    if data["filas"]:
                        table(data["columnas"], [[row.get(c) for c in data["columnas"]] for row in data["filas"]])
                    else:
                        empty("La consulta no devolvió filas.")
            except ApiError as exc:
                with result:
                    alert(exc.detail, "danger")

        with ui.element("div").classes("mini-actions"):
            ui.button("Ejecutar consulta", on_click=run_query).classes("primary-btn").props(
                "no-caps unelevated"
            )
            ui.button(
                "Consultar matrículas",
                on_click=lambda: (
                    sql.set_value(
                        "SELECT m.id_matricula, u.nombre, p.nombre AS periodo, m.estado, m.total_creditos "
                        "FROM matricula m JOIN estudiante e ON e.id_estudiante = m.id_estudiante "
                        "JOIN usuario u ON u.id_usuario = e.id_usuario "
                        "JOIN periodo_academico p ON p.id_periodo = m.id_periodo ORDER BY m.id_matricula;"
                    )
                ),
            ).classes("secondary-btn").props("no-caps")
            ui.button(
                "Consultar nodos",
                on_click=lambda: sql.set_value("SELECT nombre, estado, latencia_ms, replicacion_pct FROM nodo ORDER BY id_nodo;"),
            ).classes("secondary-btn").props("no-caps")
        result


async def render_recovery(user: dict) -> None:
    logs = await api().get("/infrastructure/logs")
    page_intro(
        "Registro de eventos del sistema. Los logs permiten reconstruir la actividad "
        "y detectar fallos de nodos, transacciones y procesos de matrícula."
    )
    kpis(
        [
            ("Eventos", len(logs), "Últimos registros"),
            ("INFO", sum(1 for log in logs if log["nivel"] == "INFO"), "Operaciones normales"),
            ("WARNING", sum(1 for log in logs if log["nivel"] == "WARNING"), "Eventos a revisar"),
            ("ERROR", sum(1 for log in logs if log["nivel"] == "ERROR"), "Fallos registrados"),
        ]
    )
    with card("Log de eventos", "Orden cronológico inverso"):
        table(
            ["Fecha", "Nivel", "Origen", "Mensaje"],
            [
                [
                    fmt_date(log["fecha"], with_time=True),
                    raw(badge_html(log["nivel"])),
                    log["origen"],
                    log["mensaje"],
                ]
                for log in logs
            ],
            empty_text="No hay eventos registrados.",
        )
    with card("Estrategia de recuperación", "Tolerancia a fallos"):
        timeline(
            [
                ("1. Detección", "El monitor identifica un nodo fuera de línea o una transacción incompleta."),
                ("2. Rollback", "Las transacciones abiertas se revierten para mantener consistencia."),
                ("3. Réplica", "Un nodo en línea asume las consultas de la sede afectada."),
                ("4. Resincronización", "Al volver el nodo, se aplican los logs pendientes."),
            ]
        )


async def render_users(user: dict) -> None:
    client = api()
    users = await client.get("/users")
    roles = await client.get("/users/roles")
    catalog = await client.get("/academic/catalog")
    role_opts = {r["id_rol"]: r["nombre"] for r in roles}
    sede_opts = options(catalog["sedes"], "nombre", "id_sede")
    carrera_opts = options(catalog["carreras"], "nombre", "id_carrera")
    plan_opts = options(catalog["planes"], "nombre", "id_plan")
    role_by_name = {r["nombre"]: r["id_rol"] for r in roles}

    page_intro(
        "Administración de usuarios y permisos. Puede crear cuentas, activar o "
        "desactivar usuarios y consultar la matriz de permisos por rol."
    )
    counts = {}
    for u in users:
        counts[u["rol"]] = counts.get(u["rol"], 0) + 1
    kpis(
        [
            ("Usuarios", len(users), "Cuentas registradas"),
            ("Administrativos", sum(counts.get(r, 0) for r in ("admin", "admin_facultad", "coordinador", "secretaria")), "Personal de gestión"),
            ("Profesores", counts.get("profesor", 0), "Personal docente"),
            ("Estudiantes", counts.get("estudiante", 0), "Cuentas de estudiantes"),
        ]
    )

    def open_create() -> None:
        dialog, box = _dialog_card("Nuevo usuario")
        with box:
            nombre = _field("Nombre completo")
            email = _field("Correo electrónico")
            cedula = _field("Cédula / identificación")
            password = _field("Contraseña", password=True, password_toggle_button=True)
            rol = _select("Rol", role_opts, role_by_name.get("estudiante"))
            sede = _select("Sede", sede_opts)
            carrera = _select("Carrera", carrera_opts)
            plan = _select("Plan de estudio", plan_opts)
            codigo = _field("Código de estudiante (opcional)")
            anio = ui.number("Año de ingreso", value=2026, min=2000, max=2100).props("outlined dense").classes("w-full")
            student_fields = [carrera, plan, codigo, anio]

            def on_role(event) -> None:
                visible = role_opts.get(event.value) == "estudiante"
                for item in student_fields:
                    item.set_visibility(visible)

            rol.on_value_change(on_role)

            async def save() -> None:
                try:
                    payload = {
                        "nombre": nombre.value.strip(),
                        "email": email.value.strip().lower(),
                        "cedula": cedula.value.strip(),
                        "password": password.value,
                        "id_rol": int(rol.value),
                        "id_sede": int(sede.value) if sede.value else None,
                    }
                    if role_opts[int(rol.value)] == "estudiante":
                        payload.update(
                            {
                                "id_carrera": int(carrera.value) if carrera.value else None,
                                "id_plan": int(plan.value) if plan.value else None,
                                "codigo": codigo.value.strip() or None,
                                "anio_ingreso": int(anio.value or 2026),
                            }
                        )
                    await client.post("/users", payload)
                    dialog.close()
                    ui.notify("Usuario creado correctamente.", type="positive")
                    ui.navigate.to("/app/users")
                except (ApiError, ValueError, TypeError) as exc:
                    ui.notify(str(getattr(exc, "detail", exc)), type="negative")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancelar", on_click=dialog.close).classes("secondary-btn").props("no-caps")
                ui.button("Guardar", on_click=save).classes("primary-btn").props("no-caps unelevated")
        dialog.open()

    async def toggle_status(user_id: int, active: bool) -> None:
        try:
            await client.patch(f"/users/{user_id}/status", {"activo": not active})
            ui.notify("Estado del usuario actualizado.", type="positive")
            ui.navigate.to("/app/users")
        except ApiError as exc:
            ui.notify(exc.detail, type="negative")

    with ui.element("div").classes("mini-actions").style("margin-bottom:14px"):
        ui.button("Nuevo usuario", on_click=open_create).classes("primary-btn").props(
            "no-caps unelevated"
        )
        ui.button(
            "Ver matriz de permisos",
            on_click=lambda: ui.navigate.to("/app/users"),
        ).classes("secondary-btn").props("no-caps")

    with card("Usuarios registrados", "Cuentas y roles"):
        for item in users:
            entity_row(
                f"{item['nombre']} · {item['rol']}",
                f"{item['email']} · cédula {item['cedula']} · "
                f"{'activo' if item['activo'] else 'inactivo'} · "
                f"último acceso {fmt_date(item.get('ultimo_acceso'), with_time=True)}",
                [
                    (
                        "Desactivar" if item["activo"] else "Activar",
                        partial(toggle_status, item["id_usuario"], item["activo"]),
                        "danger" if item["activo"] else "ok",
                    )
                ],
            )

    matrix = await client.get("/users/permissions-matrix")
    with card("Matriz de permisos", "Acciones por módulo y rol"):
        table(
            ["Módulo", "Acción", "Roles con permiso"],
            [
                [row["modulo"], row["accion"], ", ".join(row["roles"])]
                for row in matrix["matriz"]
            ],
        )


async def render_academic(user: dict) -> None:
    client = api()
    catalog = await client.get("/academic/catalog")
    sedes = await client.get("/academic/sedes")
    facultades = await client.get("/academic/facultades")
    escuelas = await client.get("/academic/escuelas")
    carreras = await client.get("/academic/carreras")
    planes = await client.get("/academic/planes")
    materias = await client.get("/academic/materias")
    periodos = await client.get("/academic/periodos")

    sede_opts = options(sedes, "nombre", "id_sede")
    facultad_opts = options(facultades, "nombre", "id_facultad")
    escuela_opts = options(escuelas, "nombre", "id_escuela")
    carrera_opts = options(carreras, "nombre", "id_carrera")
    plan_opts = options(planes, "nombre", "id_plan")
    materia_opts = {m["id_materia"]: f"{m['codigo']} · {m['nombre']}" for m in materias}

    page_intro(
        "Estructura académica de la universidad: sedes, facultades, escuelas, carreras, "
        "planes de estudio, materias y períodos."
    )
    kpis(
        [
            ("Sedes", len(sedes), "Presencia regional"),
            ("Carreras", len(carreras), "Oferta académica"),
            ("Materias", len(materias), "Catálogo de asignaturas"),
            ("Períodos", len(periodos), "Calendario académico"),
        ]
    )

    def open_facultad() -> None:
        dialog, box = _dialog_card("Nueva facultad")
        with box:
            nombre = _field("Nombre")
            codigo = _field("Código")
            sede = _select("Sede", sede_opts)

            async def save() -> None:
                try:
                    await client.post(
                        "/academic/facultades",
                        {"nombre": nombre.value, "codigo": codigo.value, "id_sede": int(sede.value) if sede.value else None},
                    )
                    dialog.close()
                    ui.navigate.to("/app/academic")
                except ApiError as exc:
                    ui.notify(exc.detail, type="negative")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancelar", on_click=dialog.close).classes("secondary-btn").props("no-caps")
                ui.button("Guardar", on_click=save).classes("primary-btn").props("no-caps unelevated")
        dialog.open()

    def open_carrera() -> None:
        dialog, box = _dialog_card("Nueva carrera")
        with box:
            nombre = _field("Nombre")
            codigo = _field("Código")
            titulo = _field("Título otorgado")
            escuela = _select("Escuela", escuela_opts)

            async def save() -> None:
                try:
                    await client.post(
                        "/academic/carreras",
                        {
                            "nombre": nombre.value,
                            "codigo": codigo.value,
                            "titulo": titulo.value or None,
                            "id_escuela": int(escuela.value),
                        },
                    )
                    dialog.close()
                    ui.navigate.to("/app/academic")
                except (ApiError, TypeError) as exc:
                    ui.notify(str(getattr(exc, "detail", exc)), type="negative")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancelar", on_click=dialog.close).classes("secondary-btn").props("no-caps")
                ui.button("Guardar", on_click=save).classes("primary-btn").props("no-caps unelevated")
        dialog.open()

    def open_materia() -> None:
        dialog, box = _dialog_card("Nueva materia")
        with box:
            codigo = _field("Código", placeholder="IS-417")
            nombre = _field("Nombre")
            creditos = ui.number("Créditos", value=3, min=1, max=12).props("outlined dense").classes("w-full")
            teoricas = ui.number("Horas teóricas", value=2, min=0).props("outlined dense").classes("w-full")
            practicas = ui.number("Horas prácticas", value=2, min=0).props("outlined dense").classes("w-full")

            async def save() -> None:
                try:
                    await client.post(
                        "/academic/materias",
                        {
                            "codigo": codigo.value,
                            "nombre": nombre.value,
                            "creditos": int(creditos.value or 3),
                            "horas_teoricas": int(teoricas.value or 0),
                            "horas_practicas": int(practicas.value or 0),
                        },
                    )
                    dialog.close()
                    ui.navigate.to("/app/academic")
                except ApiError as exc:
                    ui.notify(exc.detail, type="negative")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancelar", on_click=dialog.close).classes("secondary-btn").props("no-caps")
                ui.button("Guardar", on_click=save).classes("primary-btn").props("no-caps unelevated")
        dialog.open()

    def open_plan() -> None:
        dialog, box = _dialog_card("Nuevo plan de estudio")
        with box:
            nombre = _field("Nombre", placeholder="Plan 2027")
            anio = ui.number("Año", value=2027, min=2000, max=2100).props("outlined dense").classes("w-full")
            carrera = _select("Carrera", carrera_opts)
            creditos = ui.number("Créditos totales", value=220, min=0).props("outlined dense").classes("w-full")

            async def save() -> None:
                try:
                    await client.post(
                        "/academic/planes",
                        {
                            "nombre": nombre.value,
                            "anio": int(anio.value or 2027),
                            "id_carrera": int(carrera.value),
                            "creditos_totales": int(creditos.value or 0),
                        },
                    )
                    dialog.close()
                    ui.navigate.to("/app/academic")
                except (ApiError, TypeError) as exc:
                    ui.notify(str(getattr(exc, "detail", exc)), type="negative")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancelar", on_click=dialog.close).classes("secondary-btn").props("no-caps")
                ui.button("Guardar", on_click=save).classes("primary-btn").props("no-caps unelevated")
        dialog.open()

    with ui.element("div").classes("mini-actions").style("margin-bottom:14px"):
        for label, handler in (
            ("Nueva facultad", open_facultad),
            ("Nueva carrera", open_carrera),
            ("Nueva materia", open_materia),
            ("Nuevo plan", open_plan),
        ):
            ui.button(label, on_click=handler).classes("primary-btn").props("no-caps unelevated")

    with grid("grid-2"):
        with card("Sedes", "Presencia regional"):
            table(["Sede", "Ciudad", "Provincia", "Activa"], [[s["nombre"], s.get("ciudad"), s.get("provincia"), "Sí" if s["activo"] else "No"] for s in sedes])
        with card("Facultades", "Unidades académicas"):
            table(["Facultad", "Código", "Sede"], [[f["nombre"], f["codigo"], f.get("sede") or "—"] for f in facultades])
    with grid("grid-2"):
        with card("Escuelas", "Dependencias"):
            table(["Escuela", "Código", "Facultad"], [[e["nombre"], e["codigo"], e.get("facultad") or "—"] for e in escuelas])
        with card("Carreras", "Oferta de grado"):
            table(["Carrera", "Código", "Título"], [[c["nombre"], c["codigo"], c.get("titulo") or "—"] for c in carreras])
    with grid("grid-2"):
        with card("Planes de estudio", "Versiones curriculares"):
            table(["Plan", "Año", "Créditos", "Carrera", "Estado"], [[p["nombre"], p["anio"], p["creditos_totales"], p.get("carrera") or "—", raw(badge_html(p["estado"]))] for p in planes])
        with card("Períodos", "Calendario"):
            table(["Período", "Inicio", "Fin", "Estado", "Matrícula"], [[p["nombre"], fmt_date(p["fecha_inicio"]), fmt_date(p["fecha_fin"]), raw(badge_html(p["estado"])), "Abierta" if p["matricula_abierta"] else "Cerrada"] for p in periodos])
    with card("Materias", "Catálogo de asignaturas"):
        table(
            ["Código", "Materia", "Créditos", "Horas T/P", "Prerrequisitos", "Activa"],
            [
                [
                    m["codigo"],
                    m["nombre"],
                    m["creditos"],
                    f"{m['horas_teoricas']}/{m['horas_practicas']}",
                    ", ".join(p["codigo"] for p in m.get("prerequisitos", [])) or "—",
                    "Sí" if m["activo"] else "No",
                ]
                for m in materias
            ],
        )

    with card("Agregar materia al plan", "Plan de estudios"):
        plan_sel = _select("Plan", plan_opts)
        materia_sel = _select("Materia", materia_opts)
        nivel = ui.number("Nivel", value=1, min=1).props("outlined dense").classes("w-full")

        async def add_plan_materia() -> None:
            try:
                await client.post(
                    "/academic/planes/materias",
                    {"id_plan": int(plan_sel.value), "id_materia": int(materia_sel.value), "nivel": int(nivel.value or 1)},
                )
                ui.notify("Materia agregada al plan.", type="positive")
            except (ApiError, TypeError) as exc:
                ui.notify(str(getattr(exc, "detail", exc)), type="negative")

        ui.button("Agregar al plan", on_click=add_plan_materia).classes("primary-btn").props("no-caps unelevated")


async def render_periods(user: dict) -> None:
    client = api()
    periodos = await client.get("/academic/periodos")
    page_intro(
        "Gestión del calendario académico y de la ventana de matrícula. Solo un período "
        "debe permanecer con la matrícula abierta."
    )
    current = next((p for p in periodos if p["matricula_abierta"]), None)
    kpis(
        [
            ("Períodos", len(periodos), "Registrados"),
            ("Abiertos", sum(1 for p in periodos if p["estado"] == "abierto"), "En curso"),
            ("Matrícula abierta", current["nombre"] if current else "Ninguno", "Ventana vigente"),
            ("Planificados", sum(1 for p in periodos if p["estado"] == "planificado"), "Próximos"),
        ]
    )

    async def toggle(id_periodo: int, abrir: bool) -> None:
        try:
            await client.patch(f"/academic/periodos/{id_periodo}/matricula", {"matricula_abierta": abrir})
            ui.notify("Ventana de matrícula actualizada.", type="positive")
            ui.navigate.to("/app/periods")
        except ApiError as exc:
            ui.notify(exc.detail, type="negative")

    def open_create() -> None:
        dialog, box = _dialog_card("Nuevo período")
        with box:
            nombre = _field("Nombre", placeholder="2027-II")
            anio = ui.number("Año", value=2027, min=2000, max=2100).props("outlined dense").classes("w-full")
            numero = ui.number("Número", value=2, min=1, max=3).props("outlined dense").classes("w-full")
            inicio = _field("Fecha inicio", value="2027-08-01", placeholder="AAAA-MM-DD")
            fin = _field("Fecha fin", value="2027-12-15", placeholder="AAAA-MM-DD")
            max_creditos = ui.number("Máximo de créditos", value=24, min=1).props("outlined dense").classes("w-full")
            estado = _select("Estado", {"planificado": "planificado", "abierto": "abierto", "cerrado": "cerrado"}, "planificado")

            async def save() -> None:
                try:
                    await client.post(
                        "/academic/periodos",
                        {
                            "nombre": nombre.value,
                            "anio": int(anio.value),
                            "numero": int(numero.value),
                            "fecha_inicio": inicio.value,
                            "fecha_fin": fin.value,
                            "estado": estado.value,
                            "matricula_abierta": False,
                            "max_creditos": int(max_creditos.value or 24),
                        },
                    )
                    dialog.close()
                    ui.navigate.to("/app/periods")
                except (ApiError, ValueError, TypeError) as exc:
                    ui.notify(str(getattr(exc, "detail", exc)), type="negative")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancelar", on_click=dialog.close).classes("secondary-btn").props("no-caps")
                ui.button("Guardar", on_click=save).classes("primary-btn").props("no-caps unelevated")
        dialog.open()

    ui.button("Nuevo período", on_click=open_create).classes("primary-btn").props("no-caps unelevated")
    for period in periodos:
        entity_row(
            f"{period['nombre']} · {period['estado']}",
            f"{fmt_date(period['fecha_inicio'])} al {fmt_date(period['fecha_fin'])} · "
            f"máximo {period['max_creditos']} créditos · matrícula "
            f"{'abierta' if period['matricula_abierta'] else 'cerrada'}",
            [
                (
                    "Cerrar matrícula" if period["matricula_abierta"] else "Abrir matrícula",
                    partial(toggle, period["id_periodo"], not period["matricula_abierta"]),
                    "danger" if period["matricula_abierta"] else "ok",
                )
            ],
        )


async def render_groups(user: dict) -> None:
    client = api()
    grupos = await client.get("/academic/grupos")
    catalog = await client.get("/academic/catalog")
    profesores = await client.get("/users/professors")
    aulas = await client.get("/academic/aulas")
    periodos = await client.get("/academic/periodos")

    materia_opts = {m["id_materia"]: f"{m['codigo']} · {m['nombre']}" for m in catalog["materias"]}
    periodo_opts = options(periodos, "nombre", "id_periodo")
    sede_opts = options(catalog["sedes"], "nombre", "id_sede")
    profesor_opts = {p["id_profesor"]: p["nombre"] for p in profesores}
    aula_opts = {a["id_aula"]: f"{a['nombre']} · {a['sede']}" for a in aulas}

    page_intro(
        "Oferta académica por período: grupos, cupos, docentes, aulas y horarios. "
        "La creación de un grupo permite configurar su primer horario."
    )
    kpis(
        [
            ("Grupos", len(grupos), "Oferta total"),
            ("Abiertos", sum(1 for g in grupos if g["estado"] == "abierto"), "Disponibles para matrícula"),
            ("Cupos disponibles", sum(g["cupos_disponibles"] for g in grupos), "Suma de grupos"),
            ("Profesores", len(profesores), "Docentes asignables"),
        ]
    )

    def open_create() -> None:
        dialog, box = _dialog_card("Nuevo grupo")
        with box:
            codigo = _field("Código del grupo", placeholder="IS-417-A")
            materia = _select("Materia", materia_opts)
            periodo = _select("Período", periodo_opts)
            sede = _select("Sede", sede_opts)
            profesor = _select("Profesor", profesor_opts)
            cupo = ui.number("Cupo", value=30, min=1).props("outlined dense").classes("w-full")
            aula = _select("Aula", aula_opts)
            dia = _select("Día", {d: d for d in DIAS}, "Lunes")
            inicio = _field("Hora inicio", value="16:00", placeholder="HH:MM")
            fin = _field("Hora fin", value="18:00", placeholder="HH:MM")

            async def save() -> None:
                try:
                    payload = {
                        "id_materia": int(materia.value),
                        "id_periodo": int(periodo.value),
                        "id_sede": int(sede.value),
                        "id_profesor": int(profesor.value) if profesor.value else None,
                        "codigo": codigo.value.strip(),
                        "cupo": int(cupo.value or 30),
                        "horarios": [],
                    }
                    if aula.value and inicio.value and fin.value:
                        payload["horarios"].append(
                            {
                                "id_aula": int(aula.value),
                                "dia_semana": dia.value,
                                "hora_inicio": inicio.value,
                                "hora_fin": fin.value,
                            }
                        )
                    await client.post("/academic/grupos", payload)
                    dialog.close()
                    ui.navigate.to("/app/groups")
                except (ApiError, ValueError, TypeError) as exc:
                    ui.notify(str(getattr(exc, "detail", exc)), type="negative")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancelar", on_click=dialog.close).classes("secondary-btn").props("no-caps")
                ui.button("Guardar", on_click=save).classes("primary-btn").props("no-caps unelevated")
        dialog.open()

    ui.button("Nuevo grupo", on_click=open_create).classes("primary-btn").props("no-caps unelevated")
    with card("Grupos y horarios", "Oferta por período"):
        table(
            ["Código", "Materia", "Período", "Sede", "Profesor", "Cupos", "Horario", "Estado"],
            [
                [
                    g["codigo"],
                    f"{g['codigo_materia']} · {g['materia']}",
                    g["periodo"],
                    g["sede"],
                    g.get("profesor") or "—",
                    f"{g['cupos_disponibles']}/{g['cupo']}",
                    ", ".join(
                        f"{h['dia_semana']} {h['hora_inicio']}-{h['hora_fin']}"
                        for h in g.get("horarios", [])
                    )
                    or "—",
                    raw(badge_html(g["estado"])),
                ]
                for g in grupos
            ],
        )


async def render_enrollments(user: dict) -> None:
    client = api()
    matriculas = await client.get("/enrollments")
    page_intro(
        "Matrículas registradas en todos los períodos. Secretaría puede confirmar "
        "matrículas pendientes o anularlas según las políticas académicas."
    )
    kpis(
        [
            ("Matrículas", len(matriculas), "Todos los períodos"),
            ("Confirmadas", sum(1 for m in matriculas if m["estado"] == "confirmada"), "Validadas"),
            ("Pendientes", sum(1 for m in matriculas if m["estado"] == "pendiente"), "Por confirmar"),
            ("Créditos", sum(m["total_creditos"] for m in matriculas), "Carga acumulada"),
        ]
    )

    async def confirmar(id_matricula: int) -> None:
        try:
            await client.post(f"/enrollments/{id_matricula}/confirmar")
            ui.notify("Matrícula confirmada.", type="positive")
            ui.navigate.to("/app/enrollments")
        except ApiError as exc:
            ui.notify(exc.detail, type="negative")

    async def anular(id_matricula: int) -> None:
        try:
            await client.delete(f"/enrollments/{id_matricula}")
            ui.notify("Matrícula anulada.", type="positive")
            ui.navigate.to("/app/enrollments")
        except ApiError as exc:
            ui.notify(exc.detail, type="negative")

    for matricula in matriculas:
        with card(
            f"{matricula['estudiante']} · {matricula['periodo']['nombre']}",
            f"{matricula['codigo']} · {matricula['carrera']} · {matricula['total_creditos']} créditos · {fmt_date(matricula['fecha'])}",
            matricula["estado"],
            tone_for(matricula["estado"]),
        ):
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
                empty_text="La matrícula no tiene asignaturas.",
            )
            with ui.element("div").classes("mini-actions").style("margin-top:10px"):
                if matricula["estado"] != "confirmada":
                    ui.button(
                        "Confirmar matrícula",
                        on_click=partial(confirmar, matricula["id_matricula"]),
                    ).classes("mini-btn ok").props("flat no-caps dense")
                if matricula["estado"] != "anulada":
                    ui.button(
                        "Anular matrícula",
                        on_click=partial(anular, matricula["id_matricula"]),
                    ).classes("mini-btn danger").props("flat no-caps dense")


async def render_grades(user: dict) -> None:
    client = api()
    detalles = await client.get("/grades/detalles")
    page_intro(
        "Registro y consulta de calificaciones por asignatura. Al registrar una nota "
        "se recalcula la nota final del detalle y el índice académico del estudiante."
    )
    con_nota = sum(1 for d in detalles if d.get("nota_final") is not None)
    promedio = (
        round(sum(d["nota_final"] for d in detalles if d.get("nota_final") is not None) / con_nota, 1)
        if con_nota
        else 0
    )
    kpis(
        [
            ("Detalles", len(detalles), "Asignaturas matriculadas"),
            ("Calificados", con_nota, "Con nota final"),
            ("Promedio general", promedio, "Sobre 100 puntos"),
            ("Sin calificar", len(detalles) - con_nota, "Pendientes"),
        ]
    )

    def open_grade(detalle: dict) -> None:
        dialog, box = _dialog_card(
            f"Calificar · {detalle['grupo']['codigo_materia']} {detalle['grupo']['materia']}"
        )
        with box:
            ui.html(
                f"<p style='color:var(--muted);font-size:12px'>Estudiante: "
                f"<strong>{esc(detalle['estudiante'])}</strong> · "
                f"{esc(detalle['codigo_estudiante'])}</p>"
            )
            evaluacion = _field("Evaluación", value="Nota final")
            nota = ui.number("Nota (0-100)", value=80, min=0, max=100).props("outlined dense").classes("w-full")
            ponderacion = ui.number("Ponderación (%)", value=100, min=1, max=100).props("outlined dense").classes("w-full")
            observacion = ui.textarea("Observación").props("outlined dense").classes("w-full")

            async def save() -> None:
                try:
                    await client.post(
                        "/grades",
                        {
                            "id_detalle": detalle["id_detalle"],
                            "evaluacion": evaluacion.value,
                            "nota": float(nota.value),
                            "ponderacion": float(ponderacion.value),
                            "observacion": observacion.value or None,
                        },
                    )
                    dialog.close()
                    ui.notify("Calificación registrada.", type="positive")
                    ui.navigate.to("/app/grades")
                except (ApiError, ValueError, TypeError) as exc:
                    ui.notify(str(getattr(exc, "detail", exc)), type="negative")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancelar", on_click=dialog.close).classes("secondary-btn").props("no-caps")
                ui.button("Guardar nota", on_click=save).classes("primary-btn").props("no-caps unelevated")
        dialog.open()

    with card("Detalles de matrícula", "Calificaciones por asignatura"):
        for detalle in detalles:
            grupo = detalle["grupo"]
            evaluaciones = ", ".join(
                f"{c['evaluacion']}: {c['nota']}" for c in detalle.get("calificaciones", [])
            )
            entity_row(
                f"{detalle['estudiante']} · {grupo['codigo_materia']} {grupo['materia']}",
                f"{grupo['codigo']} · {grupo['periodo']} · nota final "
                f"{detalle.get('nota_final') if detalle.get('nota_final') is not None else 'sin registrar'}"
                + (f" · {evaluaciones}" if evaluaciones else ""),
                [("Registrar nota", partial(open_grade, detalle), "ok")],
            )


async def render_payments(user: dict) -> None:
    client = api()
    pagos = await client.get("/payments")
    page_intro(
        "Control de pagos asociados a matrículas. Un pago marcado como pagado "
        "confirma automáticamente la matrícula correspondiente."
    )
    kpis(
        [
            ("Pagos", len(pagos), "Registrados"),
            ("Pagados", sum(1 for p in pagos if p["estado"] == "pagado"), "Confirmados"),
            ("Pendientes", sum(1 for p in pagos if p["estado"] == "pendiente"), "Por cobrar"),
            ("Monto total", fmt_money(sum(p["monto"] for p in pagos)), "Acumulado"),
        ]
    )

    async def change_state(id_pago: int, estado: str) -> None:
        try:
            await client.patch(f"/payments/{id_pago}/estado", {"estado": estado})
            ui.notify("Estado del pago actualizado.", type="positive")
            ui.navigate.to("/app/payments")
        except ApiError as exc:
            ui.notify(exc.detail, type="negative")

    with card("Pagos registrados", "Historial"):
        for pago in pagos:
            actions = []
            if pago["estado"] != "pagado":
                actions.append(("Marcar pagado", partial(change_state, pago["id_pago"], "pagado"), "ok"))
            if pago["estado"] != "anulado":
                actions.append(("Anular", partial(change_state, pago["id_pago"], "anulado"), "danger"))
            entity_row(
                f"{pago['estudiante']} · {fmt_money(pago['monto'])} · {pago['estado']}",
                f"{pago['periodo']} · {pago.get('metodo') or '—'} · "
                f"referencia {pago.get('referencia') or '—'} · {fmt_date(pago['fecha'])}",
                actions,
            )


async def render_audit(user: dict) -> None:
    registros = await api().get("/infrastructure/audit")
    page_intro(
        "Auditoría de las operaciones realizadas en el sistema. Cada acción registra "
        "usuario, entidad, detalle, dirección IP y fecha."
    )
    kpis(
        [
            ("Registros", len(registros), "Últimas operaciones"),
            ("Inicios de sesión", sum(1 for r in registros if r["accion"] == "LOGIN"), "LOGIN"),
            ("Creaciones", sum(1 for r in registros if r["accion"] == "CREAR"), "CREAR"),
            ("Actualizaciones", sum(1 for r in registros if r["accion"] == "ACTUALIZAR"), "ACTUALIZAR"),
        ]
    )
    with card("Registro de auditoría", "Trazabilidad"):
        table(
            ["Fecha", "Usuario", "Acción", "Entidad", "ID", "Detalle", "IP"],
            [
                [
                    fmt_date(r["fecha"], with_time=True),
                    r["usuario"],
                    raw(badge_html(r["accion"])),
                    r["entidad"],
                    r.get("entidad_id") or "—",
                    r.get("detalle") or "—",
                    r.get("ip") or "—",
                ]
                for r in registros
            ],
        )


ADMIN_RENDERERS = {
    "dashboard": render_admin_dashboard,
    "infrastructure": render_infrastructure,
    "replication": render_replication,
    "architecture": render_architecture,
    "data": render_data,
    "fragmentation": render_fragmentation,
    "transactions": render_transactions,
    "concurrency": render_concurrency,
    "queries": render_queries,
    "recovery": render_recovery,
    "users": render_users,
    "academic": render_academic,
    "periods": render_periods,
    "groups": render_groups,
    "enrollments": render_enrollments,
    "grades": render_grades,
    "payments": render_payments,
    "audit": render_audit,
}
