from __future__ import annotations

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
from schemas import ExitEventRequest, ExitEventResponse, HealthResponse
from service import DuplicateEventGuard, ExitEventDispatcher
from settings import ServiceSettings


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("vehicle-exit-service")


class CameraWorker:
    def __init__(self, settings: ServiceSettings, dispatcher: ExitEventDispatcher) -> None:
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

                    event = ExitEventRequest(
                        plate=detection.plate,
                        exit_time=datetime.now(timezone.utc),
                        source="auto-camera",
                        confidence=float(detection.confidence),
                        camera_id=self.settings.camera_id,
                    )

                    response = self.dispatcher.process_event(event, strict_forwarding=False)
                    if not response.forwarded:
                        logger.warning("Evento detectado no pudo ser reenviado: %s", response.message)
                    else:
                        logger.info("Salida enviada automaticamente para placa %s", response.plate)

                time.sleep(self.settings.camera_poll_interval_seconds)
        finally:
            cap.release()
            logger.info("Worker de camara detenido")


def create_app(settings: ServiceSettings | None = None) -> FastAPI:
    service_settings = settings or ServiceSettings.from_env()
    backend_client = MainBackendClient(
        base_url=service_settings.backend_exit_url,
        api_key=service_settings.backend_api_key,
        timeout_seconds=service_settings.request_timeout_seconds,
    )
    dispatcher = ExitEventDispatcher(
        backend_client=backend_client,
        duplicate_guard=DuplicateEventGuard(service_settings.duplicate_window_seconds),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.settings.auto_detection_enabled:
            app.state.camera_worker.start()
            logger.info("Auto deteccion de salida habilitada")
        else:
            logger.info("Auto deteccion deshabilitada (AUTO_DETECTION_ENABLED=false)")

        try:
            yield
        finally:
            app.state.camera_worker.stop()

    app = FastAPI(
        title="SIPAR Vehicle Exit Service",
        version="1.0.0",
        redirect_slashes=False,
        lifespan=lifespan,
    )
    app.state.settings = service_settings
    app.state.dispatcher = dispatcher
    app.state.camera_worker = CameraWorker(service_settings, dispatcher)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service=app.state.settings.service_name)

    @app.post("/api/v1/vehicle-exits", response_model=ExitEventResponse)
    def register_vehicle_exit(payload: ExitEventRequest, request: Request) -> ExitEventResponse:
        result = request.app.state.dispatcher.process_event(payload, strict_forwarding=True)
        if not result.accepted:
            raise RuntimeError(result.message)
        return result

    @app.exception_handler(RuntimeError)
    async def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": str(exc)},
        )

    return app


app = create_app()
