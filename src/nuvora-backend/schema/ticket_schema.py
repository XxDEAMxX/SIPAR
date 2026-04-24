from datetime import datetime

from pydantic import BaseModel


class TicketUpdate(BaseModel):
    monto_total: float | None = None
    estado: str | None = None
    tarifa_id: int | None = None
    minutos_cobrados: int | None = None


class TicketResponse(BaseModel):
    id: int
    codigo_ticket: str | None = None
    vehiculo_id: int
    placa_snapshot: str
    turno_id: int | None = None
    turno_cierre_id: int | None = None
    tarifa_id: int | None = None
    entry_event_id: int | None = None
    exit_event_id: int | None = None
    hora_entrada: datetime
    hora_salida: datetime | None = None
    minutos_cobrados: int | None = None
    monto_total: float | None = None
    estado: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
