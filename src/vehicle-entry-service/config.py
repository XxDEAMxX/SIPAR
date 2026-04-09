import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    camera_index: int
    camera_id: str
    backend_endpoint: str
    backend_timeout_seconds: float
    capture_interval_seconds: float
    plate_cooldown_seconds: float
    min_detection_confidence: float
    detector_model: str
    ocr_model: str


def load_settings() -> Settings:
    camera_index = int(os.getenv("CAMERA_INDEX", "0"))
    return Settings(
        camera_index=camera_index,
        camera_id=os.getenv("CAMERA_ID", f"cam-{camera_index}"),
        backend_endpoint=os.getenv(
            "BACKEND_ENDPOINT", "http://127.0.0.1:8000/api/plates"
        ).strip(),
        backend_timeout_seconds=float(os.getenv("BACKEND_TIMEOUT_SECONDS", "5")),
        capture_interval_seconds=float(os.getenv("CAPTURE_INTERVAL_SECONDS", "0.05")),
        plate_cooldown_seconds=float(os.getenv("PLATE_COOLDOWN_SECONDS", "3")),
        min_detection_confidence=float(os.getenv("MIN_DETECTION_CONFIDENCE", "0.3")),
        detector_model=os.getenv(
            "ALPR_DETECTOR_MODEL", "yolo-v9-t-384-license-plate-end2end"
        ),
        ocr_model=os.getenv("ALPR_OCR_MODEL", "cct-xs-v1-global-model"),
    )
