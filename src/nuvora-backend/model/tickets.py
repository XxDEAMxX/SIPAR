from sqlalchemy import Column, DateTime, DECIMAL, Enum, ForeignKey, Integer, String
from sqlalchemy.sql import func

from config.db import Base


TICKET_STATE = ("abierto", "cerrado", "pagado", "anulado")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    codigo_ticket = Column(String(32), nullable=True, unique=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False, index=True)
    placa_snapshot = Column(String(10), nullable=False, index=True)
    turno_id = Column(Integer, ForeignKey("turnos.id"), nullable=True)
    turno_cierre_id = Column(Integer, ForeignKey("turnos.id"), nullable=True, index=True)
    tarifa_id = Column(Integer, ForeignKey("tarifas.id"), nullable=True, index=True)
    entry_event_id = Column(
        Integer,
        ForeignKey("parking_events.id", use_alter=True, name="fk_tickets_entry_event"),
        nullable=True,
        unique=True,
        index=True,
    )
    exit_event_id = Column(
        Integer,
        ForeignKey("parking_events.id", use_alter=True, name="fk_tickets_exit_event"),
        nullable=True,
        unique=True,
        index=True,
    )
    hora_entrada = Column(DateTime(timezone=False), nullable=False, index=True)
    hora_salida = Column(DateTime(timezone=False), nullable=True)
    minutos_cobrados = Column(Integer, nullable=True)
    monto_total = Column(DECIMAL(10, 2), nullable=True)
    estado = Column(Enum(*TICKET_STATE, name="ticket_estado"), nullable=False, default="abierto", index=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
