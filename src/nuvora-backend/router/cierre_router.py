from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from config.auth import require_admin, require_cajero
from config.db import SessionLocal
from model.cierres import CierreCaja
from model.tickets import Ticket
from model.turnos import Turno
from model.users import User
from schema.cierre_schema import CierreCreate, CierreResponse


cierre_router = APIRouter(prefix="/cierres", tags=["Cierres"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@cierre_router.post("/", response_model=CierreResponse)
def crear_cierre(
    data: CierreCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_cajero),
):
    turno = db.query(Turno).filter(Turno.id == data.turno_id).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    if turno.estado != "cerrado":
        raise HTTPException(status_code=400, detail="El turno debe estar cerrado antes de generar un cierre")
    if turno.incluido_en_cierre:
        raise HTTPException(status_code=400, detail="El turno ya fue incluido en un cierre")

    cierre_existente = db.query(CierreCaja).filter(CierreCaja.turno_id == turno.id).first()
    if cierre_existente:
        raise HTTPException(status_code=400, detail="Ya existe un cierre para este turno")

    total_recaudado = db.query(func.coalesce(func.sum(Ticket.monto_total), 0)).filter(
        Ticket.turno_cierre_id == turno.id,
        Ticket.estado.in_(("cerrado", "pagado")),
    ).scalar() or 0
    total_vehiculos = db.query(func.count(Ticket.id)).filter(
        Ticket.turno_cierre_id == turno.id,
        Ticket.estado.in_(("cerrado", "pagado")),
    ).scalar() or 0

    cierre = CierreCaja(
        turno_id=turno.id,
        total_vehiculos=int(total_vehiculos),
        total_recaudado=float(total_recaudado),
        fecha_cierre=turno.fecha_fin or datetime.now(),
        observaciones=data.observaciones,
    )
    db.add(cierre)
    turno.incluido_en_cierre = True
    db.commit()
    db.refresh(cierre)
    return cierre


@cierre_router.get("/", response_model=list[CierreResponse])
def listar_cierres(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return db.query(CierreCaja).order_by(CierreCaja.created_at.desc()).all()


@cierre_router.get("/{cierre_id}", response_model=CierreResponse)
def obtener_cierre(
    cierre_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    cierre = db.query(CierreCaja).filter(CierreCaja.id == cierre_id).first()
    if not cierre:
        raise HTTPException(status_code=404, detail="Cierre no encontrado")
    return cierre
