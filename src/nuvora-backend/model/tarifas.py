from sqlalchemy import Boolean, Column, DateTime, DECIMAL, Enum, Integer, String, Time
from sqlalchemy.sql import func

from config.db import Base


TARIFA_TYPES = ("diurna", "nocturna")


class Tarifa(Base):
    __tablename__ = "tarifas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(80), nullable=False, unique=True)
    tipo = Column(Enum(*TARIFA_TYPES, name="tarifa_tipo"), nullable=False, index=True)
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    valor_hora = Column(DECIMAL(10, 2), nullable=False, default=0.00)
    minutos_gracia = Column(Integer, nullable=False, default=0)
    fraccion_minutos = Column(Integer, nullable=False, default=60)
    activa = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
