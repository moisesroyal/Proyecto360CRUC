"""Configuración central del backend.

Lee variables de entorno (o el archivo .env de la raíz) usando python-dotenv.
No depende de pydantic-settings para mantener el entorno mínimo.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_list(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = _env("APP_NAME", "Secretaría Virtual Académica CRUC Coclé")
    app_version: str = _env("APP_VERSION", "1.0.0")
    environment: str = _env("ENVIRONMENT", "development")
    debug: bool = _env("DEBUG", "true").lower() in {"1", "true", "yes", "on"}

    database_url: str = _env(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/secretaria_virtual",
    )
    secret_key: str = _env("SECRET_KEY", "cambia-esta-clave-en-produccion-360")
    access_token_expire_minutes: int = _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", 480)
    max_credits_default: int = _env_int("MAX_CREDITS_DEFAULT", 24)
    matricula_fee: float = _env_float("MATRICULA_FEE", 150.0)

    cors_origins: list[str] = field(
        default_factory=lambda: _env_list(
            "CORS_ORIGINS",
            "http://localhost:8080,http://127.0.0.1:8080,http://localhost:8000",
        )
    )

    seed_admin_name: str = _env("SEED_ADMIN_NAME", "Dr. Carlos Mendoza")
    seed_admin_email: str = _env("SEED_ADMIN_EMAIL", "admin@universidad.edu.pa")
    seed_admin_cedula: str = _env("SEED_ADMIN_CEDULA", "ADMIN-01")
    seed_admin_password: str = _env("SEED_ADMIN_PASSWORD", "password123")

    seed_student_name: str = _env("SEED_STUDENT_NAME", "Ana Rodríguez")
    seed_student_email: str = _env("SEED_STUDENT_EMAIL", "estudiante@universidad.edu.pa")
    seed_student_cedula: str = _env("SEED_STUDENT_CEDULA", "8-888-8888")
    seed_student_password: str = _env("SEED_STUDENT_PASSWORD", "password123")


settings = Settings()
