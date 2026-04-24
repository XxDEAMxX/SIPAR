from sqlalchemy import Column, DateTime, DECIMAL, ForeignKey, Integer, Text
from sqlalchemy.sql import func

from config.db import Base


class CierreCaja(Base):
    __tablename__ = "cierres_caja"

    id = Column(Integer, primary_key=True, index=True)
    turno_id = Column(Integer, ForeignKey("turnos.id"), nullable=False, unique=True, index=True)
    total_vehiculos = Column(Integer, nullable=False, default=0)
    total_recaudado = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    fecha_cierre = Column(DateTime(timezone=False), nullable=False, index=True)
    observaciones = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
