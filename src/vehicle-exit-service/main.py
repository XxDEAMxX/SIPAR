import logging
import os
from typing import Any

from fastapi import FastAPI

from alpr_engine import DetectionProcessor
from backend import BackendClient
from config import load_settings
from state import PlateDeduplicator
from worker import DetectionWorker

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("vehicle-entry-service")

app = FastAPI(title="Vehicle Entry Service", version="1.0.0")

settings = load_settings()
backend_client = BackendClient(settings.backend_endpoint, settings.backend_timeout_seconds)
deduplicator = PlateDeduplicator(settings.plate_cooldown_seconds)
processor = DetectionProcessor(settings, deduplicator, backend_client)
worker = DetectionWorker(settings, processor)


@app.on_event("startup")
def on_startup() -> None:
    worker.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    worker.stop()


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "camera_index": settings.camera_index,
        "camera_id": settings.camera_id,
        "backend_endpoint_configured": bool(settings.backend_endpoint),
        "worker_alive": worker.is_alive(),
    }
