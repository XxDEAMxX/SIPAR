from datetime import datetime, time

from pydantic import BaseModel


class TarifaCreate(BaseModel):
    nombre: str
    tipo: str
    hora_inicio: time
    hora_fin: time
    valor_hora: float
    minutos_gracia: int = 0
    fraccion_minutos: int = 60
    activa: bool = True


class TarifaUpdate(BaseModel):
    nombre: str | None = None
    tipo: str | None = None
    hora_inicio: time | None = None
    hora_fin: time | None = None
    valor_hora: float | None = None
    minutos_gracia: int | None = None
    fraccion_minutos: int | None = None
    activa: bool | None = None


class TarifaResponse(BaseModel):
    id: int
    nombre: str
    tipo: str
    hora_inicio: time
    hora_fin: time
    valor_hora: float
    minutos_gracia: int
    fraccion_minutos: int
    activa: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
