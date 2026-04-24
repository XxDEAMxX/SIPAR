from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from config.auth import get_current_user, require_cajero
from config.db import SessionLocal
from model.tarifas import Tarifa
from model.tickets import TICKET_STATE, Ticket
from model.users import User
from schema.ticket_schema import TicketResponse, TicketUpdate


ticket_router = APIRouter(prefix="/tickets", tags=["Tickets"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@ticket_router.get("/", response_model=list[TicketResponse])
def listar_tickets(
    estado: str | None = Query(default=None),
    placa: str | None = Query(default=None),
    codigo_ticket: str | None = Query(default=None),
    vehiculo_id: int | None = Query(default=None),
    tarifa_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if estado is not None and estado not in TICKET_STATE:
        raise HTTPException(status_code=400, detail="estado no valido")

    query = db.query(Ticket)

    if estado is not None:
        query = query.filter(Ticket.estado == estado)
    if placa:
        query = query.filter(Ticket.placa_snapshot == placa.strip().upper())
    if codigo_ticket:
        query = query.filter(Ticket.codigo_ticket == codigo_ticket.strip().upper())
    if vehiculo_id is not None:
        query = query.filter(Ticket.vehiculo_id == vehiculo_id)
    if tarifa_id is not None:
        query = query.filter(Ticket.tarifa_id == tarifa_id)

    return query.order_by(Ticket.hora_entrada.desc(), Ticket.id.desc()).all()


@ticket_router.get("/{ticket_id}", response_model=TicketResponse)
def obtener_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket


@ticket_router.get("/codigo/{codigo_ticket}", response_model=TicketResponse)
def obtener_ticket_por_codigo(
    codigo_ticket: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ticket = db.query(Ticket).filter(Ticket.codigo_ticket == codigo_ticket.strip().upper()).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket


@ticket_router.patch("/{ticket_id}", response_model=TicketResponse)
def actualizar_ticket(
    ticket_id: int,
    data: TicketUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_cajero),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    if data.estado is not None:
        estado = data.estado.strip().lower()
        if estado not in TICKET_STATE:
            raise HTTPException(status_code=400, detail="estado no valido")
        ticket.estado = estado

    if data.monto_total is not None:
        ticket.monto_total = data.monto_total
    if data.tarifa_id is not None:
        tarifa = db.query(Tarifa).filter(Tarifa.id == data.tarifa_id).first()
        if not tarifa:
            raise HTTPException(status_code=404, detail="Tarifa no encontrada")
        ticket.tarifa_id = tarifa.id
    if data.minutos_cobrados is not None:
        if data.minutos_cobrados < 0:
            raise HTTPException(status_code=400, detail="minutos_cobrados no puede ser negativo")
        ticket.minutos_cobrados = data.minutos_cobrados

    db.commit()
    db.refresh(ticket)
    return ticket
