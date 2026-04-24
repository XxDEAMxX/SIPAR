from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from config.auth import create_access_token, get_current_user, require_cajero
from config.db import SessionLocal
from model.tickets import Ticket
from model.turnos import TURN_STATE, Turno
from model.users import User
from schema.turno_schema import TurnoCloseRequest, TurnoOpenRequest, TurnoResponse, TurnoTokenResponse


turno_router = APIRouter(prefix="/turnos", tags=["Turnos"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def build_turno_token_response(turno: Turno, current_user: User, include_turno_id: bool) -> TurnoTokenResponse:
    token_payload = {
        "sub": str(current_user.id),
        "rol": current_user.rol,
    }
    if include_turno_id:
        token_payload["turno_id"] = turno.id

    return TurnoTokenResponse(
        id=turno.id,
        usuario_id=turno.usuario_id,
        fecha_inicio=turno.fecha_inicio,
        fecha_fin=turno.fecha_fin,
        monto_inicial=float(turno.monto_inicial) if turno.monto_inicial is not None else None,
        monto_total=float(turno.monto_total) if turno.monto_total is not None else None,
        total_vehiculos=turno.total_vehiculos or 0,
        incluido_en_cierre=bool(turno.incluido_en_cierre),
        estado=turno.estado,
        observaciones=turno.observaciones,
        created_at=turno.created_at,
        access_token=create_access_token(token_payload),
        token_type="bearer",
    )


def get_turno_totals(db: Session, turno_id: int) -> tuple[float, int]:
    total_recaudado = db.query(func.coalesce(func.sum(Ticket.monto_total), 0)).filter(
        Ticket.turno_cierre_id == turno_id,
        Ticket.estado.in_(("cerrado", "pagado")),
    ).scalar() or 0
    total_vehiculos = db.query(func.count(Ticket.id)).filter(
        Ticket.turno_cierre_id == turno_id,
        Ticket.estado.in_(("cerrado", "pagado")),
    ).scalar() or 0
    return float(total_recaudado), int(total_vehiculos)


def get_open_turno_for_user(db: Session, user_id: int) -> Turno | None:
    return (
        db.query(Turno)
        .filter(Turno.usuario_id == user_id, Turno.estado == "abierto")
        .order_by(Turno.fecha_inicio.desc(), Turno.id.desc())
        .first()
    )


@turno_router.post("/iniciar", response_model=TurnoTokenResponse)
def iniciar_turno(
    data: TurnoOpenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_cajero),
):
    turno_abierto = get_open_turno_for_user(db, current_user.id)
    if turno_abierto:
        raise HTTPException(status_code=400, detail="El usuario ya tiene un turno abierto")

    nuevo_turno = Turno(
        usuario_id=current_user.id,
        fecha_inicio=datetime.now(),
        monto_inicial=data.monto_inicial,
        observaciones=data.observaciones,
        estado="abierto",
        incluido_en_cierre=False,
        total_vehiculos=0,
    )
    db.add(nuevo_turno)
    db.commit()
    db.refresh(nuevo_turno)
    return build_turno_token_response(nuevo_turno, current_user, include_turno_id=True)


@turno_router.post("/cerrar", response_model=TurnoTokenResponse)
def cerrar_mi_turno(
    data: TurnoCloseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_cajero),
):
    turno = get_open_turno_for_user(db, current_user.id)
    if not turno:
        raise HTTPException(status_code=404, detail="No tienes un turno abierto para cerrar")

    total_recaudado, total_vehiculos = get_turno_totals(db, turno.id)
    turno.fecha_fin = datetime.now()
    turno.estado = "cerrado"
    turno.monto_total = total_recaudado
    turno.total_vehiculos = total_vehiculos
    if data.observaciones is not None:
        turno.observaciones = data.observaciones

    db.commit()
    db.refresh(turno)
    return build_turno_token_response(turno, current_user, include_turno_id=False)


@turno_router.get("/actual", response_model=TurnoResponse)
def obtener_turno_actual(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    turno = get_open_turno_for_user(db, current_user.id)
    if not turno:
        raise HTTPException(status_code=404, detail="No tienes un turno abierto actualmente")

    total_recaudado, total_vehiculos = get_turno_totals(db, turno.id)
    turno.monto_total = total_recaudado
    turno.total_vehiculos = total_vehiculos
    return turno


@turno_router.get("/", response_model=list[TurnoResponse])
def listar_turnos(
    estado: str | None = Query(default=None),
    usuario_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if estado is not None and estado not in TURN_STATE:
        raise HTTPException(status_code=400, detail="estado debe ser 'abierto' o 'cerrado'")

    query = db.query(Turno)

    if current_user.rol != "admin":
        query = query.filter(Turno.usuario_id == current_user.id)
    elif usuario_id is not None:
        query = query.filter(Turno.usuario_id == usuario_id)

    if estado is not None:
        query = query.filter(Turno.estado == estado)

    return query.order_by(Turno.fecha_inicio.desc(), Turno.id.desc()).all()


@turno_router.get("/{turno_id}", response_model=TurnoResponse)
def obtener_turno(
    turno_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    turno = db.query(Turno).filter(Turno.id == turno_id).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    if current_user.rol != "admin" and turno.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes permiso para consultar este turno")

    total_recaudado, total_vehiculos = get_turno_totals(db, turno.id)
    turno.monto_total = total_recaudado
    turno.total_vehiculos = total_vehiculos
    return turno
