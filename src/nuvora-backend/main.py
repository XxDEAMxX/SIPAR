import logging
import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router.event_router import event_router
from router.user_router import user
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from werkzeug.security import check_password_hash, generate_password_hash

from config.db import Base, SessionLocal, engine
import model.users
import model.turnos
from model.users import User


logger = logging.getLogger(__name__)


def _upsert_default_user(
    db,
    username: str,
    password: str,
    nombre: str,
    rol: str,
    force_password_reset: bool,
) -> None:
    existing = db.query(User).filter(User.usuario == username).first()
    password_hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=30)

    if existing:
        changed = False
        if existing.rol != rol:
            existing.rol = rol
            changed = True
        if existing.activo is False:
            existing.activo = True
            changed = True
        if force_password_reset and not check_password_hash(existing.password_hash, password):
            existing.password_hash = password_hash
            changed = True

        if changed:
            db.commit()
            logger.info("Default user '%s' updated successfully.", username)
        else:
            logger.info("Default user '%s' already configured.", username)
        return

    user = User(
        nombre=nombre,
        rol=rol,
        usuario=username,
        password_hash=password_hash,
        activo=True,
    )
    db.add(user)
    db.commit()
    logger.info("Default user '%s' created successfully.", username)


def bootstrap_default_users() -> None:
    """Create or reconcile default users for local/dev startup."""
    users_enabled = os.getenv("DEFAULT_USERS_BOOTSTRAP_ENABLED", "true").lower() in {"1", "true", "yes"}
    if not users_enabled:
        logger.info("Default users bootstrap disabled by DEFAULT_USERS_BOOTSTRAP_ENABLED")
        return

    force_password_reset = os.getenv("DEFAULT_USERS_FORCE_PASSWORD_RESET", "true").lower() in {
        "1",
        "true",
        "yes",
    }

    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin1234")
    admin_nombre = os.getenv("ADMIN_NOMBRE", "Administrador")

    operator_username = os.getenv("OPERATOR_USERNAME", "operador")
    operator_password = os.getenv("OPERATOR_PASSWORD", "Operador1234")
    operator_nombre = os.getenv("OPERATOR_NOMBRE", "Operador")

    db = SessionLocal()
    try:
        _upsert_default_user(
            db=db,
            username=admin_username,
            password=admin_password,
            nombre=admin_nombre,
            rol="admin",
            force_password_reset=force_password_reset,
        )
        _upsert_default_user(
            db=db,
            username=operator_username,
            password=operator_password,
            nombre=operator_nombre,
            rol="vigilante",
            force_password_reset=force_password_reset,
        )
    finally:
        db.close()


def wait_for_database(max_retries: int = 30, delay_seconds: int = 2) -> None:
    """Wait until MySQL is reachable to avoid startup race conditions."""
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Database connection established.")
            return
        except OperationalError:
            logger.warning(
                "Database not ready (attempt %s/%s). Retrying in %ss...",
                attempt,
                max_retries,
                delay_seconds,
            )
            time.sleep(delay_seconds)

    raise RuntimeError("Database did not become ready in time")

app = FastAPI(title="User Authentication API", redirect_slashes=False)

# Habilitar CORS para permitir conexiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica los dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear las tablas en la base de datos
wait_for_database()
Base.metadata.create_all(bind=engine)
bootstrap_default_users()

# Incluir el enrutador de usuarios
app.include_router(user, prefix="/api")
app.include_router(event_router, prefix="/api")