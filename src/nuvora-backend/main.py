import logging
import os
import time
from pathlib import Path


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_APP_DIR = Path(__file__).resolve().parent
_load_env_file(_APP_DIR.parent / ".env")
_load_env_file(_APP_DIR / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router.parking_router import parking_router
from router.plate_detection_router import plate_detection_router
from router.user_router import user
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from werkzeug.security import generate_password_hash

from config.db import Base, SessionLocal, engine
import model.parking_events
import model.users
import model.tickets
import model.turnos
import model.vehiculos
import model.plate_detections
from model.users import User


logger = logging.getLogger(__name__)


def bootstrap_admin_user() -> None:
    """Create an initial admin user once when env vars are provided."""
    admin_enabled = os.getenv("ADMIN_BOOTSTRAP_ENABLED", "true").lower() in {"1", "true", "yes"}
    if not admin_enabled:
        logger.info("Admin bootstrap disabled by ADMIN_BOOTSTRAP_ENABLED")
        return

    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD")
    admin_nombre = os.getenv("ADMIN_NOMBRE", "Administrador")

    if not admin_password:
        logger.warning("ADMIN_PASSWORD is not set. Skipping admin bootstrap.")
        return

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.usuario == admin_username).first()
        if existing:
            if existing.rol != "admin" or existing.activo is False:
                existing.rol = "admin"
                existing.activo = True
                db.commit()
                logger.info("Existing user '%s' promoted/activated as admin.", admin_username)
            else:
                logger.info("Admin user '%s' already exists.", admin_username)
            return

        password_hash = generate_password_hash(admin_password, method="pbkdf2:sha256", salt_length=30)
        admin_user = User(
            nombre=admin_nombre,
            rol="admin",
            usuario=admin_username,
            password_hash=password_hash,
            activo=True,
        )
        db.add(admin_user)
        db.commit()
        logger.info("Admin user '%s' created successfully.", admin_username)
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
bootstrap_admin_user()

# Incluir el enrutador de usuarios
app.include_router(user, prefix="/api")
app.include_router(plate_detection_router, prefix="/api")
app.include_router(parking_router, prefix="/api")
