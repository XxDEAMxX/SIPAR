from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EntryEventRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    plate: str = Field(..., min_length=5, max_length=10, description="Placa detectada o registrada manualmente")
    entry_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Hora de entrada del vehiculo",
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


class EntryEventResponse(BaseModel):
    accepted: bool
    duplicate: bool
    forwarded: bool
    message: str
    plate: str
    entry_time: datetime


class EntryEventItem(BaseModel):
    plate: str
    entry_time: datetime
    source: str
    confidence: float | None = None
    forwarded: bool
    duplicate: bool
    message: str


class RecentEntryEventsResponse(BaseModel):
    total: int
    items: list[EntryEventItem]


class FrameDetectionRequest(BaseModel):
    image_base64: str = Field(..., min_length=20)
    min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    camera_id: str | None = Field(default=None, max_length=64)


class FrameDetectionItem(BaseModel):
    plate: str
    confidence: float
    forwarded: bool
    duplicate: bool
    message: str


class FrameDetectionResponse(BaseModel):
    processed: int
    items: list[FrameDetectionItem]
    message: str


class HealthResponse(BaseModel):
    status: str
    service: str
