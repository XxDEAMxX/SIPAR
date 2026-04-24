from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from config.db import Base


PARKING_EVENT_DIRECTION = ("entry", "exit")
PARKING_EVENT_STATUS = ("processed", "ignored", "error")


class ParkingEvent(Base):
    __tablename__ = "parking_events"

    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"), nullable=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True, index=True)
    detection_id = Column(Integer, ForeignKey("placas_detectadas.id"), nullable=True, index=True)
    plate = Column(String(20), nullable=False, index=True)
    direction = Column(Enum(*PARKING_EVENT_DIRECTION, name="parking_event_direction"), nullable=False, index=True)
    status = Column(Enum(*PARKING_EVENT_STATUS, name="parking_event_status"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    camera_id = Column(String(50), nullable=True, index=True)
    source = Column(String(50), nullable=True)
    detected_at = Column(DateTime(timezone=False), nullable=False, index=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
