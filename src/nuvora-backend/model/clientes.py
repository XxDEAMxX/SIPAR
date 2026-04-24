from sqlalchemy import Column, DateTime, Enum, Integer, String
from sqlalchemy.sql import func

from config.db import Base


CLIENTE_TYPES = ("visitante", "abonado")


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, index=True)
    telefono = Column(String(15), nullable=True)
    correo = Column(String(100), nullable=True, unique=True, index=True)
    tipo_cliente = Column(
        Enum(*CLIENTE_TYPES, name="cliente_tipo"),
        nullable=False,
        default="visitante",
        index=True,
    )
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
