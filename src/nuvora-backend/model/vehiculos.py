from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from config.db import Base


class Vehiculo(Base):
    __tablename__ = "vehiculos"

    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String(10), nullable=False, unique=True, index=True)
    propietario_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
