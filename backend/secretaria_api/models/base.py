"""Clase base declarativa y mixins comunes."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .enums import enum_values


class Base(DeclarativeBase):
    pass


def enum_column(enum_cls: type[Enum], length: int = 20):
    """Columna Enum que persiste el valor literal en VARCHAR (sin tipo nativo)."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=enum_values,
        validate_strings=True,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
