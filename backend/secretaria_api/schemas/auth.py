from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, description="Correo, cédula o nombre de usuario")
    password: str = Field(min_length=8)


class RegisterRequest(BaseModel):
    nombre: str = Field(min_length=3, max_length=160)
    email: str = Field(min_length=5, max_length=160)
    cedula: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=8, max_length=128)
    telefono: str | None = Field(default=None, max_length=40)
    id_carrera: int | None = None
    id_plan: int | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Correo electrónico inválido")
        return value


class UserSession(BaseModel):
    id_usuario: int
    nombre: str
    email: str
    cedula: str
    rol: str
    rol_id: int
    activo: bool
    id_estudiante: int | None = None
    id_profesor: int | None = None
    ultimo_acceso: datetime | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSession


class UserMe(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    nombre: str
    email: str
    cedula: str
    telefono: str | None = None
    activo: bool
