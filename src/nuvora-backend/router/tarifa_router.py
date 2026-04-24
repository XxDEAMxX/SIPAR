from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from config.auth import get_current_user, require_admin
from config.db import SessionLocal
from model.tarifas import TARIFA_TYPES, Tarifa
from model.users import User
from schema.tarifa_schema import TarifaCreate, TarifaResponse, TarifaUpdate


tarifa_router = APIRouter(prefix="/tarifas", tags=["Tarifas"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validate_tarifa_payload(tipo: str | None, minutos_gracia: int | None, fraccion_minutos: int | None) -> str | None:
    tipo_normalizado = tipo.strip().lower() if tipo is not None else None
    if tipo_normalizado is not None and tipo_normalizado not in TARIFA_TYPES:
        raise HTTPException(status_code=400, detail="tipo debe ser 'diurna' o 'nocturna'")
    if minutos_gracia is not None and minutos_gracia < 0:
        raise HTTPException(status_code=400, detail="minutos_gracia no puede ser negativo")
    if fraccion_minutos is not None and fraccion_minutos <= 0:
        raise HTTPException(status_code=400, detail="fraccion_minutos debe ser mayor que 0")
    return tipo_normalizado


@tarifa_router.post("/", response_model=TarifaResponse)
def crear_tarifa(
    data: TarifaCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    tipo = validate_tarifa_payload(data.tipo, data.minutos_gracia, data.fraccion_minutos)
    nombre = data.nombre.strip()

    existente = db.query(Tarifa).filter(Tarifa.nombre == nombre).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe una tarifa con ese nombre")

    tarifa = Tarifa(
        nombre=nombre,
        tipo=tipo,
        hora_inicio=data.hora_inicio,
        hora_fin=data.hora_fin,
        valor_hora=data.valor_hora,
        minutos_gracia=data.minutos_gracia,
        fraccion_minutos=data.fraccion_minutos,
        activa=data.activa,
    )
    db.add(tarifa)
    db.commit()
    db.refresh(tarifa)
    return tarifa


@tarifa_router.get("/", response_model=list[TarifaResponse])
def listar_tarifas(
    activas: bool | None = Query(default=None),
    tipo: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    tipo_normalizado = validate_tarifa_payload(tipo, None, None)
    query = db.query(Tarifa)
    if activas is not None:
        query = query.filter(Tarifa.activa == activas)
    if tipo_normalizado is not None:
        query = query.filter(Tarifa.tipo == tipo_normalizado)
    return query.order_by(Tarifa.id.asc()).all()


@tarifa_router.get("/{tarifa_id}", response_model=TarifaResponse)
def obtener_tarifa(
    tarifa_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    tarifa = db.query(Tarifa).filter(Tarifa.id == tarifa_id).first()
    if not tarifa:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")
    return tarifa


@tarifa_router.put("/{tarifa_id}", response_model=TarifaResponse)
def actualizar_tarifa(
    tarifa_id: int,
    data: TarifaUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    tarifa = db.query(Tarifa).filter(Tarifa.id == tarifa_id).first()
    if not tarifa:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")

    tipo = validate_tarifa_payload(data.tipo, data.minutos_gracia, data.fraccion_minutos)

    if data.nombre is not None:
        nombre = data.nombre.strip()
        existente = db.query(Tarifa).filter(Tarifa.nombre == nombre, Tarifa.id != tarifa_id).first()
        if existente:
            raise HTTPException(status_code=400, detail="Ya existe una tarifa con ese nombre")
        tarifa.nombre = nombre
    if tipo is not None:
        tarifa.tipo = tipo
    if data.hora_inicio is not None:
        tarifa.hora_inicio = data.hora_inicio
    if data.hora_fin is not None:
        tarifa.hora_fin = data.hora_fin
    if data.valor_hora is not None:
        tarifa.valor_hora = data.valor_hora
    if data.minutos_gracia is not None:
        tarifa.minutos_gracia = data.minutos_gracia
    if data.fraccion_minutos is not None:
        tarifa.fraccion_minutos = data.fraccion_minutos
    if data.activa is not None:
        tarifa.activa = data.activa

    db.commit()
    db.refresh(tarifa)
    return tarifa
