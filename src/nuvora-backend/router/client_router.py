from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from config.auth import require_admin
from config.db import SessionLocal
from model.clientes import CLIENTE_TYPES, Cliente
from model.users import User
from schema.cliente_schema import ClienteCreate, ClienteResponse, ClienteUpdate


client_router = APIRouter(prefix="/clientes", tags=["Clientes"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validate_tipo_cliente(tipo_cliente: str | None) -> str | None:
    if tipo_cliente is None:
        return None
    tipo_normalizado = tipo_cliente.strip().lower()
    if tipo_normalizado not in CLIENTE_TYPES:
        raise HTTPException(status_code=400, detail="tipo_cliente debe ser 'visitante' o 'abonado'")
    return tipo_normalizado


@client_router.post("/", response_model=ClienteResponse)
def crear_cliente(
    data: ClienteCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    tipo_cliente = validate_tipo_cliente(data.tipo_cliente) or "visitante"
    correo = str(data.correo).strip().lower() if data.correo else None

    if correo:
        existente = db.query(Cliente).filter(Cliente.correo == correo).first()
        if existente:
            raise HTTPException(status_code=400, detail="Ya existe un cliente con ese correo")

    nuevo_cliente = Cliente(
        nombre=data.nombre.strip(),
        telefono=data.telefono.strip() if data.telefono else None,
        correo=correo,
        tipo_cliente=tipo_cliente,
    )
    db.add(nuevo_cliente)
    db.commit()
    db.refresh(nuevo_cliente)
    return nuevo_cliente


@client_router.get("/", response_model=list[ClienteResponse])
def listar_clientes(
    tipo: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Cliente)
    tipo_cliente = validate_tipo_cliente(tipo)
    if tipo_cliente:
        query = query.filter(Cliente.tipo_cliente == tipo_cliente)
    return query.order_by(Cliente.created_at.desc()).all()


@client_router.get("/{cliente_id}", response_model=ClienteResponse)
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@client_router.put("/{cliente_id}", response_model=ClienteResponse)
def actualizar_cliente(
    cliente_id: int,
    data: ClienteUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if data.nombre is not None:
        cliente.nombre = data.nombre.strip()
    if data.telefono is not None:
        cliente.telefono = data.telefono.strip() or None
    if data.correo is not None:
        correo = str(data.correo).strip().lower()
        existente = db.query(Cliente).filter(Cliente.correo == correo, Cliente.id != cliente_id).first()
        if existente:
            raise HTTPException(status_code=400, detail="Ese correo ya está en uso")
        cliente.correo = correo
    if data.tipo_cliente is not None:
        cliente.tipo_cliente = validate_tipo_cliente(data.tipo_cliente)

    db.commit()
    db.refresh(cliente)
    return cliente


@client_router.delete("/{cliente_id}")
def eliminar_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    db.delete(cliente)
    db.commit()
    return {"ok": True}


@client_router.get("/buscar/correo/{correo}", response_model=ClienteResponse)
def buscar_por_correo(correo: str, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.correo == correo.strip().lower()).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado con ese correo")
    return cliente
