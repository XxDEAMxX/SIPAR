import os
from dataclasses import dataclass
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


_SERVICE_DIR = Path(__file__).resolve().parent
_load_env_file(_SERVICE_DIR.parent / ".env")
_load_env_file(_SERVICE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    camera_source: int | str
    camera_id: str
    backend_endpoint: str
    backend_timeout_seconds: float
    service_api_key: str
    detection_direction: str
    source_name: str
    capture_interval_seconds: float
    plate_cooldown_seconds: float
    consensus_window_seconds: float
    consensus_min_observations: int
    consensus_min_support: int
    consensus_min_confidence: float
    min_plate_confidence: float
    immediate_emit_plate_confidence: float
    immediate_emit_min_hits: int
    post_emit_lock_seconds: float
    presence_reset_seconds: float
    min_detection_confidence: float
    detector_model: str
    ocr_model: str


def load_settings() -> Settings:
    raw_camera_source = os.getenv("CAMERA_SOURCE", "http://127.0.0.1:8010/cameras/salida/stream").strip()
    camera_source: int | str = int(raw_camera_source) if raw_camera_source.isdigit() else raw_camera_source
    return Settings(
        camera_source=camera_source,
        camera_id=os.getenv("CAMERA_ID", "salida"),
        backend_endpoint=os.getenv(
            "BACKEND_ENDPOINT", "http://127.0.0.1:8000/api/parking/detections"
        ).strip(),
        backend_timeout_seconds=float(os.getenv("BACKEND_TIMEOUT_SECONDS", "5")),
        service_api_key=os.getenv("SERVICE_API_KEY", "nuvora-service-key-2024-change-in-prod").strip(),
        detection_direction=os.getenv("DETECTION_DIRECTION", "exit").strip().lower(),
        source_name=os.getenv("SOURCE_NAME", "vehicle-exit-service").strip(),
        capture_interval_seconds=float(os.getenv("CAPTURE_INTERVAL_SECONDS", "0.05")),
        plate_cooldown_seconds=float(os.getenv("PLATE_COOLDOWN_SECONDS", "3")),
        consensus_window_seconds=float(os.getenv("CONSENSUS_WINDOW_SECONDS", "1.0")),
        consensus_min_observations=int(os.getenv("CONSENSUS_MIN_OBSERVATIONS", "2")),
        consensus_min_support=int(os.getenv("CONSENSUS_MIN_SUPPORT", "3")),
        consensus_min_confidence=float(os.getenv("CONSENSUS_MIN_CONFIDENCE", "0.9")),
        min_plate_confidence=float(os.getenv("MIN_PLATE_CONFIDENCE", "0.6")),
        immediate_emit_plate_confidence=float(os.getenv("IMMEDIATE_EMIT_PLATE_CONFIDENCE", "0.98")),
        immediate_emit_min_hits=int(os.getenv("IMMEDIATE_EMIT_MIN_HITS", "2")),
        post_emit_lock_seconds=float(os.getenv("POST_EMIT_LOCK_SECONDS", "4.0")),
        presence_reset_seconds=float(os.getenv("PRESENCE_RESET_SECONDS", "2.0")),
        min_detection_confidence=float(os.getenv("MIN_DETECTION_CONFIDENCE", "0.3")),
        detector_model=os.getenv(
            "ALPR_DETECTOR_MODEL", "yolo-v9-t-384-license-plate-end2end"
        ),
        ocr_model=os.getenv("ALPR_OCR_MODEL", "cct-xs-v1-global-model"),
    )
