import logging
import threading
import time

import cv2

from alpr_engine import DetectionProcessor, create_alpr
from config import Settings


logger = logging.getLogger("vehicle-entry-service")


class DetectionWorker:
    def __init__(self, settings: Settings, processor: DetectionProcessor) -> None:
        self.settings = settings
        self.processor = processor
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._thread.start()
        logger.info("Worker iniciado")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        logger.info("Worker detenido")

    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _detection_loop(self) -> None:
        logger.info("Inicializando ALPR")
        alpr = create_alpr(self.settings)

        logger.info("Abriendo fuente de video %s", self.settings.camera_source)
        cap = cv2.VideoCapture(self.settings.camera_source)
        if not cap.isOpened():
            logger.error("No se pudo abrir la fuente de video %s", self.settings.camera_source)
            return

        try:
            while not self._stop_event.is_set():
                ok, frame = cap.read()
                if not ok:
                    logger.warning("No se pudo leer frame")
                    self.processor.flush_pending()
                    time.sleep(0.2)
                    continue

                try:
                    results = alpr.predict(frame)
                except Exception:
                    logger.exception("Error en inferencia")
                    self.processor.flush_pending()
                    time.sleep(0.2)
                    continue

                for result in results:
                    self.processor.handle_result(result)

                self.processor.flush_pending()
                time.sleep(self.settings.capture_interval_seconds)
        finally:
            self.processor.flush_pending()
            cap.release()
            logger.info("Camara liberada")
