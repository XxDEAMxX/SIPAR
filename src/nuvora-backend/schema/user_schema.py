from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    nombre: str
    rol: str
    usuario: str
    password: str


class UserResponse(BaseModel):
    id: int
    nombre: str
    rol: str
    usuario: str
    activo: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
