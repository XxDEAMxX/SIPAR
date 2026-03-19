from sqlalchemy import Column, Integer, ForeignKey, DateTime, DECIMAL, Enum, Text, Boolean
from sqlalchemy.sql import func
from config.db import Base

TURN_STATE = ('abierto', 'cerrado')


class Turno(Base):
	__tablename__ = 'turnos'

	id = Column(Integer, primary_key=True, index=True)
	usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
	fecha_inicio = Column(DateTime(timezone=False), nullable=False)
	fecha_fin = Column(DateTime(timezone=False), nullable=True)
	monto_inicial = Column(DECIMAL(10,2), nullable=False, default=0.00)
	monto_total = Column(DECIMAL(10,2), nullable=True)
	total_vehiculos = Column(Integer, nullable=False, default=0)
	incluido_en_cierre = Column(Boolean, nullable=False, default=False)
	estado = Column(Enum(*TURN_STATE, name='turno_estado'), nullable=False, default='abierto')
	observaciones = Column(Text, nullable=True)
	created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
