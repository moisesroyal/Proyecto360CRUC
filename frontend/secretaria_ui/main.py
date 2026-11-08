"""Aplicación NiceGUI de la Secretaría Virtual Académica."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from nicegui import ui

from .config import settings
from .pages import login as _login  # noqa: F401  (registra la página /login)
from .pages import portal as _portal  # noqa: F401  (registra /app/{section})

app = FastAPI(title=settings.title)


@app.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse(url="/login")


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok", "app": settings.title}


ui.run_with(
    app,
    title=settings.title,
    language="es",
    dark=False,
    storage_secret=settings.storage_secret,
    show_welcome_message=False,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "secretaria_ui.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
