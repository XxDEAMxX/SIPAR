from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean
from sqlalchemy.sql import func
from config.db import Base

# Usamos una ENUM compatible con la definición en init_schema.sql
ROLE_ENUM = ('admin', 'cajero', 'vigilante')

class User(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    rol = Column(Enum(*ROLE_ENUM, name='rol'), nullable=False)
    usuario = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)
