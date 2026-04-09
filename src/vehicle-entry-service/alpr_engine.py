import logging
from datetime import datetime, timezone
from typing import Any

import onnxruntime as ort
from fast_alpr import ALPR

from backend import BackendClient
from config import Settings
from state import PlateDeduplicator


logger = logging.getLogger("vehicle-entry-service")


def resolve_onnx_providers() -> list[str]:
    available = ort.get_available_providers()
    if "CUDAExecutionProvider" in available:
        logger.info("Usando GPU (CUDAExecutionProvider)")
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    logger.info("Usando CPUExecutionProvider")
    return ["CPUExecutionProvider"]


def create_alpr(settings: Settings) -> ALPR:
    providers = resolve_onnx_providers()
    return ALPR(
        detector_model=settings.detector_model,
        ocr_model=settings.ocr_model,
        detector_providers=providers,
        ocr_providers=providers,
    )


def normalize_confidence(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list) and value:
        return float(sum(value) / len(value))
    return None


class DetectionProcessor:
    def __init__(
        self,
        settings: Settings,
        deduplicator: PlateDeduplicator,
        backend_client: BackendClient,
    ) -> None:
        self.settings = settings
        self.deduplicator = deduplicator
        self.backend_client = backend_client

    def handle_result(self, result: Any) -> None:
        ocr = getattr(result, "ocr", None)
        detection = getattr(result, "detection", None)
        if ocr is None:
            return

        plate = (getattr(ocr, "text", "") or "").strip().upper()
        if not plate:
            return

        detection_confidence = normalize_confidence(
            getattr(detection, "confidence", None)
        )
        if (
            detection_confidence is not None
            and detection_confidence < self.settings.min_detection_confidence
        ):
            return

        if not self.deduplicator.should_emit(plate):
            return

        conf_text = (
            f"{detection_confidence:.3f}"
            if detection_confidence is not None
            else "N/A"
        )
        print(f"Placa detectada: {plate} | confianza={conf_text}", flush=True)

        payload = {
            "plate": plate,
            "detection_confidence": detection_confidence,
            "camera_id": self.settings.camera_id,
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }
        self.backend_client.send_detection(payload)
