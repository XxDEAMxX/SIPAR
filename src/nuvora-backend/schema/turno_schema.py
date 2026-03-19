from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class IniciarTurnoRequest(BaseModel):
	"""Request para iniciar un turno"""
	monto_inicial: float
	observaciones: Optional[str] = None


class TurnoCreate(BaseModel):
	usuario_id: Optional[int] = None
	fecha_inicio: Optional[datetime] = None
	monto_inicial: Optional[float] = 0.0
	observaciones: Optional[str] = None


class TurnoResponse(BaseModel):
	id: int
	usuario_id: Optional[int]
	fecha_inicio: datetime
	fecha_fin: Optional[datetime]
	monto_inicial: Optional[float]
	monto_total: Optional[float]
	total_vehiculos: Optional[int] = 0
	incluido_en_cierre: Optional[bool] = False
	estado: str
	observaciones: Optional[str]
	created_at: Optional[datetime]

	class Config:
		from_attributes = True


class TurnoIniciadoResponse(BaseModel):
	"""Respuesta al iniciar un turno, incluye el turno y un nuevo token JWT"""
	id: int
	usuario_id: Optional[int]
	fecha_inicio: datetime
	fecha_fin: Optional[datetime]
	monto_inicial: Optional[float]
	monto_total: Optional[float]
	total_vehiculos: Optional[int] = 0
	incluido_en_cierre: Optional[bool] = False
	estado: str
	observaciones: Optional[str]
	created_at: Optional[datetime]
	access_token: str  # Nuevo token con turno_id
	token_type: str = "bearer"

	class Config:
		from_attributes = True


class TurnoCerradoResponse(BaseModel):
	"""Respuesta al cerrar un turno, incluye el turno cerrado y un nuevo token JWT sin turno_id"""
	id: int
	usuario_id: Optional[int]
	fecha_inicio: datetime
	fecha_fin: Optional[datetime]
	monto_inicial: Optional[float]
	monto_total: Optional[float]
	total_vehiculos: Optional[int] = 0
	incluido_en_cierre: Optional[bool] = False
	estado: str
	observaciones: Optional[str]
	created_at: Optional[datetime]
	access_token: str  # Nuevo token SIN turno_id (para poder abrir nuevo turno)
	token_type: str = "bearer"

	class Config:
		from_attributes = True
