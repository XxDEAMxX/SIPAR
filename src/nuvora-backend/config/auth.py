import os
from datetime import datetime, timedelta
from typing import Optional, Union

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from config.db import SessionLocal
from model.users import User

# Variables de entorno
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# API Key para comunicación entre microservicios
SERVICE_API_KEY = os.getenv("SERVICE_API_KEY", "nuvora-service-key-2024-change-in-prod")

# Definir permisos por servicio
SERVICE_PERMISSIONS = {
    "nuvora-service-key-2024-change-in-prod": ["read:users", "read:vehicles", "read:tickets", "write:events"],
    "voice-service-key": ["read:users", "read:tickets"],  # Solo lectura de usuarios y tickets
    "camera-service-key": ["read:vehicles", "write:events"]  # Sin acceso a usuarios
}

# Usamos HTTPBearer para autenticación JWT (permite que sea opcional)
security = HTTPBearer(auto_error=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autorizado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[int] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or user.activo is False:
        raise credentials_exception
    return user


# Dependencias para verificar roles específicos
def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Verifica que el usuario actual sea admin"""
    if current_user.rol != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador para realizar esta acción"
        )
    return current_user


def require_cajero(current_user: User = Depends(get_current_user)) -> User:
    """Verifica que el usuario actual sea cajero o admin"""
    if current_user.rol not in ['cajero', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo cajeros y administradores pueden realizar esta acción"
        )
    return current_user


def require_vigilante(current_user: User = Depends(get_current_user)) -> User:
    """Verifica que el usuario actual sea vigilante o admin"""
    if current_user.rol not in ['vigilante', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo vigilantes y administradores pueden realizar esta acción"
        )
    return current_user


# ========== AUTENTICACIÓN PARA MICROSERVICIOS ==========

def verify_service_api_key(x_api_key: str = Header(...)) -> bool:
    """
    Verifica que la API Key del microservicio sea válida.
    Se espera que el header X-API-Key contenga la clave correcta.
    """
    if x_api_key != SERVICE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida para servicio interno"
        )
    return True


def get_current_user_or_service(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> Union[User, dict]:
    """
    Permite autenticación dual: JWT de usuario o API Key de servicio.
    Retorna el User si es JWT, o dict con permisos si es API Key válida.
    """
    # Si viene API Key, validar servicio
    if x_api_key:
        if x_api_key in SERVICE_PERMISSIONS:
            return {
                "type": "service",
                "api_key": x_api_key,
                "permissions": SERVICE_PERMISSIONS[x_api_key]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key inválida"
            )
    
    # Si no hay API Key, validar JWT de usuario
    if credentials:
        token = credentials.credentials
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: Optional[int] = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user is None or user.activo is False:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            return user
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    
    # Si no hay ninguno
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Se requiere autenticación (JWT o API Key)"
    )