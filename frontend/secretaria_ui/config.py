"""Configuración del frontend NiceGUI."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class FrontendSettings:
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    storage_secret: str = os.getenv(
        "STORAGE_SECRET", "secretaria-virtual-nicegui-storage-secret"
    )
    title: str = os.getenv("UI_TITLE", "Universidad Distribuida 360°")
    host: str = os.getenv("UI_HOST", "0.0.0.0")
    port: int = int(os.getenv("UI_PORT", "8080"))


settings = FrontendSettings()
