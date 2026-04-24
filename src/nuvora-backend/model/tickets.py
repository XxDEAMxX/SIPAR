from sqlalchemy import Column, DateTime, DECIMAL, Enum, ForeignKey, Integer
from sqlalchemy.sql import func

from config.db import Base


TICKET_STATE = ("abierto", "cerrado")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=False, index=True)
    turno_id = Column(Integer, ForeignKey("turnos.id"), nullable=True)
    hora_entrada = Column(DateTime(timezone=False), nullable=False, index=True)
    hora_salida = Column(DateTime(timezone=False), nullable=True)
    monto_total = Column(DECIMAL(10, 2), nullable=True)
    estado = Column(Enum(*TICKET_STATE, name="ticket_estado"), nullable=False, default="abierto", index=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
