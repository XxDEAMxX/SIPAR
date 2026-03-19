from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from config.db import SessionLocal
from config.auth import get_current_user, require_admin, require_cajero, create_access_token
from model.users import User
from schema.turno_schema import TurnoCreate, TurnoResponse, TurnoIniciadoResponse, IniciarTurnoRequest, TurnoCerradoResponse
from model.turnos import Turno
from model.tickets import Ticket
from typing import List
from datetime import datetime

turno_router = APIRouter(prefix="/turnos", tags=["Turnos"])


def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()


@turno_router.post("/iniciar", response_model=TurnoIniciadoResponse)
def iniciar_turno(
	data: IniciarTurnoRequest,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""
	Inicia un turno para el usuario autenticado.
	Ya no necesitas pasar user_id manualmente - se obtiene del token JWT.
	Devuelve el turno creado Y un nuevo token JWT con el turno_id incluido.
	"""
	# Verificar si el usuario ya tiene un turno abierto
	turno_abierto = db.query(Turno).filter(
		Turno.usuario_id == current_user.id,
		Turno.estado == 'abierto'
	).first()
	
	if turno_abierto:
		raise HTTPException(
			status_code=400,
			detail=f"El usuario ya tiene un turno abierto (ID: {turno_abierto.id})"
		)
	
	# Crear el turno con el usuario autenticado
	nuevo_turno = Turno(
		usuario_id=current_user.id,
		fecha_inicio=datetime.now(),
		monto_inicial=data.monto_inicial,
		observaciones=data.observaciones,
		estado='abierto'
	)
	db.add(nuevo_turno)
	db.commit()
	db.refresh(nuevo_turno)
	
	# Crear nuevo token con turno_id
	nuevo_token = create_access_token({
		"sub": str(current_user.id),
		"rol": current_user.rol,
		"turno_id": nuevo_turno.id
	})
	
	# Crear respuesta con el turno y el token
	return TurnoIniciadoResponse(
		id=nuevo_turno.id,
		usuario_id=nuevo_turno.usuario_id,
		fecha_inicio=nuevo_turno.fecha_inicio,
		fecha_fin=nuevo_turno.fecha_fin,
		monto_inicial=nuevo_turno.monto_inicial,
		monto_total=nuevo_turno.monto_total,
		estado=nuevo_turno.estado,
		observaciones=nuevo_turno.observaciones,
		created_at=nuevo_turno.created_at,
		access_token=nuevo_token,
		token_type="bearer"
	)


@turno_router.post("/", response_model=TurnoResponse)
def crear_turno(
	data: TurnoCreate,
	db: Session = Depends(get_db),
	admin: User = Depends(require_admin)
):
	"""
	Crear turno manualmente (solo para administradores).
	Los usuarios normales deben usar /iniciar.
	"""
	nueva = Turno(
		usuario_id=data.usuario_id,
		fecha_inicio=data.fecha_inicio if data.fecha_inicio else datetime.now(),
		monto_inicial=data.monto_inicial,
		observaciones=data.observaciones
	)
	db.add(nueva)
	db.commit()
	db.refresh(nueva)
	return nueva


@turno_router.get("/todos", response_model=List[TurnoResponse])
def listar_todos_turnos(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
	"""
	Lista TODOS los turnos de todos los usuarios (solo administradores).
	"""
	return db.query(Turno).all()


@turno_router.get("/actual", response_model=TurnoResponse)
def obtener_turno_actual(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
	"""
	Obtiene el turno actualmente abierto del usuario autenticado.
	Calcula las ganancias en tiempo real basándose en los tickets cerrados hasta el momento.
	Útil para saber si tiene un turno activo y cuál es.
	"""
	turno_actual = db.query(Turno).filter(
		Turno.usuario_id == current_user.id,
		Turno.estado == 'abierto'
	).first()
	
	if not turno_actual:
		raise HTTPException(status_code=404, detail="No tienes un turno abierto actualmente")
	
	# Calcular ganancias actuales (tickets cerrados en este turno)
	total_recaudado_actual = db.query(func.coalesce(func.sum(Ticket.monto_total), 0)).filter(
		Ticket.turno_cierre_id == turno_actual.id,
		Ticket.estado == 'cerrado'
	).scalar() or 0
	
	total_vehiculos_actual = db.query(func.count(Ticket.id)).filter(
		Ticket.turno_cierre_id == turno_actual.id,
		Ticket.estado == 'cerrado'
	).scalar() or 0
	
	# Actualizar los valores temporalmente para la respuesta (sin guardar en BD)
	turno_actual.monto_total = float(total_recaudado_actual)
	turno_actual.total_vehiculos = int(total_vehiculos_actual)
	
	return turno_actual


@turno_router.post("/{turno_id}/cerrar", response_model=TurnoResponse)
def cerrar_turno(
	turno_id: int,
	db: Session = Depends(get_db),
	current_user: User = Depends(get_current_user)
):
	"""
	Cierra el turno especificado.
	Solo el dueño del turno o un admin puede cerrarlo.
	"""
	turno = db.query(Turno).filter(Turno.id == turno_id).first()
	if not turno:
		raise HTTPException(status_code=404, detail="Turno no encontrado")
	
	# Verificar permisos: solo el dueño o admin puede cerrar
	if turno.usuario_id != current_user.id and current_user.rol != 'admin':
		raise HTTPException(
			status_code=403,
			detail="No tienes permiso para cerrar este turno"
		)
	
	if turno.estado == 'cerrado':
		raise HTTPException(status_code=400, detail="El turno ya está cerrado")

	turno.fecha_fin = datetime.now()
	turno.estado = 'cerrado'
	db.commit()
	db.refresh(turno)
	return turno


# Endpoint para cerrar el turno abierto del usuario autenticado
@turno_router.post("/cerrar", response_model=TurnoCerradoResponse)
def cerrar_mi_turno(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Cierra el turno abierto del usuario autenticado (no requiere id manual).
    Calcula automáticamente el monto_total basado en los tickets cerrados.
    Devuelve un nuevo token JWT SIN turno_id para permitir abrir un nuevo turno.
    """
    turno = db.query(Turno).filter(
        Turno.usuario_id == current_user.id,
        Turno.estado == 'abierto'
    ).first()
    
    if not turno:
        raise HTTPException(status_code=404, detail="No tienes un turno abierto para cerrar")
    
    # Calcular totales basados en tickets que este turno cerró
    total_recaudado = db.query(func.coalesce(func.sum(Ticket.monto_total), 0)).filter(
        Ticket.turno_cierre_id == turno.id,
        Ticket.estado == 'cerrado'
    ).scalar() or 0
    
    total_vehiculos = db.query(func.count(Ticket.id)).filter(
        Ticket.turno_cierre_id == turno.id,
        Ticket.estado == 'cerrado'
    ).scalar() or 0
    
    # Cerrar el turno con los datos calculados
    turno.fecha_fin = datetime.now()
    turno.estado = 'cerrado'
    turno.monto_total = float(total_recaudado)
    turno.total_vehiculos = int(total_vehiculos)
    turno.incluido_en_cierre = False  # Aún no ha sido incluido en un cierre
    
    try:
        db.commit()
        db.refresh(turno)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al cerrar turno: {str(e)}")
    
    # Crear nuevo token SIN turno_id (solo con user_id y rol)
    nuevo_token = create_access_token({
        "sub": str(current_user.id),
        "rol": current_user.rol
    })
    
    # Retornar turno cerrado con el nuevo token
    return TurnoCerradoResponse(
        id=turno.id,
        usuario_id=turno.usuario_id,
        fecha_inicio=turno.fecha_inicio,
        fecha_fin=turno.fecha_fin,
        monto_inicial=turno.monto_inicial,
        monto_total=turno.monto_total,
        total_vehiculos=turno.total_vehiculos,
        incluido_en_cierre=turno.incluido_en_cierre,
        estado=turno.estado,
        observaciones=turno.observaciones,
        created_at=turno.created_at,
        access_token=nuevo_token,
        token_type="bearer"
    )

