"""Cliente HTTP del frontend hacia la API FastAPI."""
from __future__ import annotations

from typing import Any

import httpx

from .config import settings


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class ApiClient:
    def __init__(self, token: str | None = None, base_url: str | None = None):
        self.token = token
        self.base_url = (base_url or settings.backend_url).rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> Any:
        url = f"{self.base_url}/api{path}"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.request(
                    method,
                    url,
                    json=json,
                    params=params,
                    headers=self._headers(),
                )
        except httpx.RequestError as exc:
            raise ApiError(503, f"No se pudo conectar con el backend: {exc}") from exc

        if response.status_code >= 400:
            detail = "Error inesperado del servidor."
            try:
                payload = response.json()
                detail = payload.get("detail", detail)
                if isinstance(detail, list):
                    detail = "; ".join(str(item) for item in detail)
            except ValueError:
                detail = response.text or detail
            raise ApiError(response.status_code, str(detail))
        if response.status_code == 204:
            return None
        if not response.content:
            return None
        return response.json()

    async def get(self, path: str, params: dict | None = None) -> Any:
        return await self.request("GET", path, params=params)

    async def post(self, path: str, json: dict | None = None) -> Any:
        return await self.request("POST", path, json=json)

    async def patch(self, path: str, json: dict | None = None) -> Any:
        return await self.request("PATCH", path, json=json)

    async def delete(self, path: str) -> Any:
        return await self.request("DELETE", path)


async def login(identifier: str, password: str) -> dict:
    return await ApiClient().post(
        "/auth/login", {"identifier": identifier, "password": password}
    )


async def register(payload: dict) -> dict:
    return await ApiClient().post("/auth/register", payload)
