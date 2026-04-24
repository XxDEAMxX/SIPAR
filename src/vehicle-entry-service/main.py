import logging
import os
from typing import Any

from fastapi import FastAPI

from alpr_engine import DetectionProcessor
from backend import BackendClient
from config import load_settings
from state import PlateConsensusBuffer, PlateDeduplicator, PlatePresenceTracker
from worker import DetectionWorker

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("vehicle-entry-service")

app = FastAPI(title="Vehicle Entry Service", version="1.0.0")

settings = load_settings()
backend_client = BackendClient(
    settings.backend_endpoint,
    settings.backend_timeout_seconds,
    settings.service_api_key,
)
deduplicator = PlateDeduplicator(settings.plate_cooldown_seconds)
consensus_buffer = PlateConsensusBuffer(
    settings.consensus_window_seconds,
    settings.consensus_min_observations,
)
presence_tracker = PlatePresenceTracker(settings.presence_reset_seconds)
processor = DetectionProcessor(settings, deduplicator, consensus_buffer, presence_tracker, backend_client)
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
        "camera_source": settings.camera_source,
        "camera_id": settings.camera_id,
        "direction": settings.detection_direction,
        "consensus_window_seconds": settings.consensus_window_seconds,
        "consensus_min_observations": settings.consensus_min_observations,
        "consensus_min_support": settings.consensus_min_support,
        "consensus_min_confidence": settings.consensus_min_confidence,
        "min_plate_confidence": settings.min_plate_confidence,
        "immediate_emit_plate_confidence": settings.immediate_emit_plate_confidence,
        "immediate_emit_min_hits": settings.immediate_emit_min_hits,
        "post_emit_lock_seconds": settings.post_emit_lock_seconds,
        "presence_reset_seconds": settings.presence_reset_seconds,
        "backend_endpoint_configured": bool(settings.backend_endpoint),
        "worker_alive": worker.is_alive(),
    }
