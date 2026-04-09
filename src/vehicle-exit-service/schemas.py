from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExitEventRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    plate: str = Field(..., min_length=5, max_length=10, description="Placa detectada o registrada manualmente")
    exit_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Hora de salida del vehiculo",
    )
    source: Literal["manual", "auto-camera"] = "manual"
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    camera_id: str | None = Field(default=None, max_length=64)

    @field_validator("plate")
    @classmethod
    def normalize_plate(cls, value: str) -> str:
        normalized = value.replace(" ", "").replace("-", "").upper()
        if not normalized.isalnum():
            raise ValueError("La placa debe contener solo letras y numeros")
        return normalized


class ExitEventResponse(BaseModel):
    accepted: bool
    duplicate: bool
    forwarded: bool
    message: str
    plate: str
    exit_time: datetime


class HealthResponse(BaseModel):
    status: str
    service: str
