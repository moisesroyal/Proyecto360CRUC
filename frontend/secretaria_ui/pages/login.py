"""Página de inicio de sesión y registro."""
from __future__ import annotations

from nicegui import ui

from ..api_client import ApiError, login, register
from ..session import is_authenticated, set_session
from ..theme import apply_theme


def _field(label: str, **kwargs) -> tuple[ui.element, ui.input]:
    with ui.element("div").classes("auth-field") as wrapper:
        ui.html(f"<label>{label}</label>")
        control = ui.input(**kwargs).props("outlined dense")
    return wrapper, control


@ui.page("/login")
async def login_page() -> None:
    apply_theme()
    ui.page_title("Acceso · Universidad Distribuida 360°")
    if is_authenticated():
        ui.navigate.to("/app/dashboard")
        return

    mode = {"value": "login"}

    with ui.element("div").classes("auth-body"):
        with ui.element("main").classes("auth-shell"):
            with ui.element("section").classes("auth-brand"):
                ui.html('<div class="auth-logo">🎓</div>')
                ui.html("<h1>Universidad<br>Distribuida 360°</h1>")
                ui.html(
                    "<p>Plataforma de gestión académica multisede.<br>"
                    "<small>La capa distribuida se presenta como simulación académica.</small></p>"
                )
                ui.html(
                    "<ul class=\"auth-features\">"
                    "<li>✓ Matrícula y calificaciones</li>"
                    "<li>✓ Pagos y auditoría</li>"
                    "<li>✓ Control de roles y sedes</li>"
                    "</ul>"
                )

            with ui.element("section").classes("auth-panel"):
                ui.html("<h2>Portal académico</h2>")
                subtitle = ui.html(
                    '<p class="auth-subtitle">Accede al sistema completando tus datos.</p>'
                )

                with ui.element("div").classes("auth-tabs"):
                    login_tab = ui.button("Iniciar sesión").classes("auth-tab active").props(
                        "flat no-caps"
                    )
                    register_tab = ui.button("Registrarse").classes("auth-tab").props(
                        "flat no-caps"
                    )

                with ui.element("div").classes("auth-form"):
                    name_wrap, name = _field(
                        "Nombre completo", placeholder="Escriba su nombre"
                    )
                    identifier_wrap, identifier = _field(
                        "Correo electrónico o identificación",
                        placeholder="Correo o número de cédula",
                    )
                    email_wrap, email = _field(
                        "Correo electrónico institucional", placeholder="correo@universidad.edu.pa"
                    )
                    cedula_wrap, cedula = _field(
                        "Número de identificación", placeholder="Número de cédula"
                    )
                    password_wrap, password = _field(
                        "Contraseña", placeholder="Mínimo 8 caracteres", password=True,
                        password_toggle_button=True,
                    )
                    confirm_wrap, confirm = _field(
                        "Confirmar contraseña", placeholder="Repite tu contraseña",
                        password=True, password_toggle_button=True,
                    )

                    message = ui.label("").classes("auth-message")
                    submit = ui.button("Entrar al sistema").classes("auth-submit").props(
                        "flat no-caps"
                    )

                    register_fields = [name_wrap, email_wrap, cedula_wrap, confirm_wrap]
                    for wrapper in register_fields:
                        wrapper.set_visibility(False)

                ui.html(
                    '<p class="auth-footer">Sitio web de prueba de matrícula, hecho por '
                    "<strong>Estudiantes de Ingeniería en Informática</strong>.</p>"
                )
                ui.html(
                    '<div class="login-hint demo-access"><strong>Acceso de demostración</strong><br>'
                    "Administrador: <code>admin@universidad.edu.pa</code> / "
                    "<code>password123</code><br>"
                    "Estudiante: <code>estudiante@universidad.edu.pa</code> / "
                    "<code>password123</code></div>"
                )

    def set_mode(value: str) -> None:
        mode["value"] = value
        is_login = value == "login"
        login_tab.classes(add="active" if is_login else "", remove="" if is_login else "active")
        register_tab.classes(
            add="" if is_login else "active", remove="active" if is_login else ""
        )
        identifier_wrap.set_visibility(is_login)
        for wrapper in register_fields:
            wrapper.set_visibility(not is_login)
        if is_login:
            subtitle.set_content(
                '<p class="auth-subtitle">Accede al sistema completando tus datos.</p>'
            )
            submit.set_text("Entrar al sistema")
        else:
            subtitle.set_content(
                '<p class="auth-subtitle">Crea tu cuenta de estudiante para iniciar.</p>'
            )
            submit.set_text("Crear cuenta")
        message.set_text("")
        message.classes(remove="error success")

    login_tab.on_click(lambda: set_mode("login"))
    register_tab.on_click(lambda: set_mode("register"))

    async def do_submit() -> None:
        message.set_text("")
        message.classes(remove="error success")
        submit.disable()
        try:
            if mode["value"] == "login":
                if len(identifier.value.strip()) < 3:
                    raise ValueError("Ingrese su correo o número de cédula.")
                if len(password.value) < 8:
                    raise ValueError("La contraseña debe tener al menos 8 caracteres.")
                data = await login(identifier.value.strip(), password.value)
            else:
                if len(name.value.strip()) < 3:
                    raise ValueError("Ingrese su nombre completo.")
                if "@" not in email.value or "." not in email.value.split("@")[-1]:
                    raise ValueError("Ingrese un correo electrónico válido.")
                if len(cedula.value.strip()) < 3:
                    raise ValueError("Ingrese su número de identificación.")
                if len(password.value) < 8:
                    raise ValueError("La contraseña debe tener al menos 8 caracteres.")
                if password.value != confirm.value:
                    raise ValueError("Las contraseñas no coinciden.")
                data = await register(
                    {
                        "nombre": name.value.strip(),
                        "email": email.value.strip().lower(),
                        "cedula": cedula.value.strip(),
                        "password": password.value,
                    }
                )
            set_session(data["access_token"], data["user"])
            ui.notify(f"Bienvenido(a), {data['user']['nombre']}", type="positive")
            ui.navigate.to("/app/dashboard")
        except ValueError as exc:
            message.set_text(str(exc))
            message.classes(add="error")
        except ApiError as exc:
            message.set_text(exc.detail)
            message.classes(add="error")
        finally:
            submit.enable()

    submit.on_click(do_submit)
