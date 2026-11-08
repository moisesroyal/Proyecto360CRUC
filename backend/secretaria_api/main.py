"""Punto de entrada del backend FastAPI."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routers import (
    academic,
    auth,
    dashboard,
    enrollment,
    grades,
    infrastructure,
    payments,
    users,
)
from .core.config import settings
from .core.database import engine
from .models import Base


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "API de la Secretaría Virtual Académica del CRUC Coclé. "
            "Implementa los módulos de usuarios, estructura académica, matrícula, "
            "profesores, períodos, calificaciones, pagos, auditoría e infraestructura."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["Sistema"])
    def health() -> dict:
        return {"status": "ok", "app": settings.app_name, "version": settings.app_version}

    @app.get("/", tags=["Sistema"])
    def root() -> dict:
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/health",
        }

    for router in (
        auth.router,
        dashboard.router,
        academic.router,
        users.router,
        enrollment.router,
        grades.router,
        payments.router,
        infrastructure.router,
    ):
        app.include_router(router, prefix="/api")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("secretaria_api.main:app", host="0.0.0.0", port=8000, reload=True)
