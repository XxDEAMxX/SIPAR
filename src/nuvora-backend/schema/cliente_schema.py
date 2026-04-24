from datetime import datetime

from pydantic import BaseModel, EmailStr


class ClienteCreate(BaseModel):
    nombre: str
    telefono: str | None = None
    correo: EmailStr | None = None
    tipo_cliente: str = "visitante"


class ClienteUpdate(BaseModel):
    nombre: str | None = None
    telefono: str | None = None
    correo: EmailStr | None = None
    tipo_cliente: str | None = None


class ClienteResponse(BaseModel):
    id: int
    nombre: str
    telefono: str | None = None
    correo: str | None = None
    tipo_cliente: str
    created_at: datetime | None = None

    class Config:
        from_attributes = True
