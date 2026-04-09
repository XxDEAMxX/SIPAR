from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from config.auth import verify_service_api_key

logger = logging.getLogger(__name__)


event_router = APIRouter(prefix="/events", tags=["Eventos internos"])


class VehicleExitEventRequest(BaseModel):
    placa: str = Field(..., min_length=5, max_length=10)
    hora_salida: datetime
    fuente: str | None = Field(default="auto-camera", max_length=32)
    confianza: float | None = Field(default=None, ge=0.0, le=1.0)
    camera_id: str | None = Field(default=None, max_length=64)

    @field_validator("placa")
    @classmethod
    def normalize_plate(cls, value: str) -> str:
        normalized = value.replace("-", "").replace(" ", "").upper()
        if not normalized.isalnum():
            raise ValueError("La placa solo puede contener letras y numeros")
        return normalized


@event_router.post("/vehicle-exit")
def receive_vehicle_exit_event(
    payload: VehicleExitEventRequest,
    _: bool = Depends(verify_service_api_key),
):
    """
    Recibe eventos de salida desde microservicios (camara, edge, etc.).
    En este sprint se deja el receptor listo para integracion SOA y trazabilidad.
    """
    logger.info(
        "Evento salida recibido | placa=%s hora=%s fuente=%s confianza=%s camera=%s",
        payload.placa,
        payload.hora_salida.isoformat(),
        payload.fuente,
        payload.confianza,
        payload.camera_id,
    )

    return {
        "accepted": True,
        "message": "Evento de salida recibido en backend principal",
        "placa": payload.placa,
        "hora_salida": payload.hora_salida,
    }
