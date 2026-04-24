from datetime import datetime

from pydantic import BaseModel


class CierreCreate(BaseModel):
    turno_id: int
    observaciones: str | None = None


class CierreResponse(BaseModel):
    id: int
    turno_id: int
    total_vehiculos: int
    total_recaudado: float
    fecha_cierre: datetime
    observaciones: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True
