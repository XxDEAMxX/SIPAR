from __future__ import annotations

import base64
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend_client import MainBackendClient
from detector import build_detector
from schemas import (
    EntryEventRequest,
    EntryEventResponse,
    FrameDetectionItem,
    FrameDetectionRequest,
    FrameDetectionResponse,
    HealthResponse,
    RecentEntryEventsResponse,
)
from service import DuplicateEventGuard, EntryEventDispatcher, EntryEventRecorder
from settings import ServiceSettings


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("vehicle-entry-service")


class CameraWorker:
    def __init__(self, settings: ServiceSettings, dispatcher: EntryEventDispatcher) -> None:
        self.settings = settings
        self.dispatcher = dispatcher
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="camera-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        import cv2

        detector = build_detector(
            provider=self.settings.detector_provider,
            mock_file=os.getenv("MOCK_DETECTIONS_FILE"),
        )

        cap = cv2.VideoCapture(self.settings.camera_index)
        if not cap.isOpened():
            logger.error("No se pudo abrir la camara %s", self.settings.camera_index)
            return

        logger.info("Worker de camara iniciado en indice %s", self.settings.camera_index)
        try:
            while not self._stop_event.is_set():
                ok, frame = cap.read()
                if not ok:
                    logger.warning("No fue posible leer frame de camara")
                    time.sleep(self.settings.camera_poll_interval_seconds)
                    continue

                detections = detector.detect(frame)
                for detection in detections:
                    if detection.confidence < self.settings.camera_min_confidence:
                        continue

                    event = EntryEventRequest(
                        plate=detection.plate,
                        entry_time=datetime.now(timezone.utc),
                        source="auto-camera",
                        confidence=float(detection.confidence),
                        camera_id=self.settings.camera_id,
                    )

                    response = self.dispatcher.process_event(event, strict_forwarding=False)
                    if not response.forwarded:
                        logger.warning("Evento detectado no pudo ser reenviado: %s", response.message)
                    else:
                        logger.info("Entrada enviada automaticamente para placa %s", response.plate)

                time.sleep(self.settings.camera_poll_interval_seconds)
        finally:
            cap.release()
            logger.info("Worker de camara detenido")


def create_app(settings: ServiceSettings | None = None) -> FastAPI:
    service_settings = settings or ServiceSettings.from_env()
    event_recorder = EntryEventRecorder(max_items=200)
    backend_client = MainBackendClient(
        base_url=service_settings.backend_entry_url,
        api_key=service_settings.backend_api_key,
        timeout_seconds=service_settings.request_timeout_seconds,
    )
    dispatcher = EntryEventDispatcher(
        backend_client=backend_client,
        duplicate_guard=DuplicateEventGuard(service_settings.duplicate_window_seconds),
        event_recorder=event_recorder,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.settings.auto_detection_enabled:
            app.state.camera_worker.start()
            logger.info("Auto deteccion de entrada habilitada")
        else:
            logger.info("Auto deteccion deshabilitada (AUTO_DETECTION_ENABLED=false)")

        try:
            yield
        finally:
            app.state.camera_worker.stop()

    app = FastAPI(
        title="SIPAR Vehicle Entry Service",
        version="1.0.0",
        redirect_slashes=False,
        lifespan=lifespan,
    )
    app.state.settings = service_settings
    app.state.dispatcher = dispatcher
    app.state.camera_worker = CameraWorker(service_settings, dispatcher)
    app.state.event_recorder = event_recorder
    app.state.frame_detector = build_detector(
        provider=service_settings.detector_provider,
        mock_file=os.getenv("MOCK_DETECTIONS_FILE"),
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service=app.state.settings.service_name)

    @app.post("/api/v1/vehicle-entries", response_model=EntryEventResponse)
    def register_vehicle_entry(payload: EntryEventRequest, request: Request) -> EntryEventResponse:
        result = request.app.state.dispatcher.process_event(payload, strict_forwarding=True)
        if not result.accepted:
            raise RuntimeError(result.message)
        return result

    @app.get("/api/v1/vehicle-entries/recent", response_model=RecentEntryEventsResponse)
    def get_recent_vehicle_entries(request: Request, limit: int = 20) -> RecentEntryEventsResponse:
        safe_limit = max(1, min(limit, 100))
        items = request.app.state.event_recorder.list_recent(limit=safe_limit)
        return RecentEntryEventsResponse(total=len(items), items=items)

    @app.post("/api/v1/vehicle-entries/detect-frame", response_model=FrameDetectionResponse)
    def detect_vehicle_entry_from_frame(
        payload: FrameDetectionRequest,
        request: Request,
    ) -> FrameDetectionResponse:
        import cv2
        import numpy as np

        encoded = payload.image_base64
        if "," in encoded:
            encoded = encoded.split(",", 1)[1]

        try:
            image_bytes = base64.b64decode(encoded)
        except Exception as exc:
            raise RuntimeError(f"Frame base64 invalido: {exc}")

        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise RuntimeError("No fue posible decodificar el frame")

        min_conf = payload.min_confidence
        if min_conf is None:
            min_conf = request.app.state.settings.camera_min_confidence

        detections = request.app.state.frame_detector.detect(frame)
        items: list[FrameDetectionItem] = []

        for detection in detections:
            if detection.confidence < min_conf:
                continue

            event = EntryEventRequest(
                plate=detection.plate,
                entry_time=datetime.now(timezone.utc),
                source="auto-camera",
                confidence=float(detection.confidence),
                camera_id=payload.camera_id or request.app.state.settings.camera_id,
            )

            result = request.app.state.dispatcher.process_event(event, strict_forwarding=False)
            items.append(
                FrameDetectionItem(
                    plate=result.plate,
                    confidence=float(detection.confidence),
                    forwarded=result.forwarded,
                    duplicate=result.duplicate,
                    message=result.message,
                )
            )

        return FrameDetectionResponse(
            processed=len(items),
            items=items,
            message="Frame procesado correctamente",
        )

    @app.exception_handler(RuntimeError)
    async def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": str(exc)},
        )

    return app


app = create_app()
