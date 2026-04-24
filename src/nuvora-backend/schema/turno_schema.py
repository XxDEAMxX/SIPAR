from datetime import datetime

from pydantic import BaseModel


class TurnoOpenRequest(BaseModel):
    monto_inicial: float = 0.0
    observaciones: str | None = None


class TurnoCloseRequest(BaseModel):
    observaciones: str | None = None


class TurnoResponse(BaseModel):
    id: int
    usuario_id: int | None = None
    fecha_inicio: datetime
    fecha_fin: datetime | None = None
    monto_inicial: float | None = None
    monto_total: float | None = None
    total_vehiculos: int = 0
    incluido_en_cierre: bool = False
    estado: str
    observaciones: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class TurnoTokenResponse(TurnoResponse):
    access_token: str
    token_type: str = "bearer"
