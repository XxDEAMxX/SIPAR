from __future__ import annotations

import os
from dataclasses import dataclass


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _to_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _to_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class ServiceSettings:
    service_name: str
    backend_entry_url: str
    backend_api_key: str
    request_timeout_seconds: float
    duplicate_window_seconds: int
    auto_detection_enabled: bool
    detector_provider: str
    camera_index: int
    camera_poll_interval_seconds: float
    camera_min_confidence: float
    camera_id: str

    @classmethod
    def from_env(cls) -> "ServiceSettings":
        return cls(
            service_name=os.getenv("SERVICE_NAME", "vehicle-entry-service"),
            backend_entry_url=os.getenv(
                "BACKEND_ENTRY_URL",
                "http://backend:8000/api/events/vehicle-entry",
            ),
            backend_api_key=os.getenv("SERVICE_API_KEY", "nuvora-service-key-2024-change-in-prod"),
            request_timeout_seconds=_to_float(os.getenv("REQUEST_TIMEOUT_SECONDS"), 5.0),
            duplicate_window_seconds=_to_int(os.getenv("DUPLICATE_WINDOW_SECONDS"), 20),
            auto_detection_enabled=_to_bool(os.getenv("AUTO_DETECTION_ENABLED"), False),
            detector_provider=os.getenv("DETECTOR_PROVIDER", "fast-alpr").strip().lower(),
            camera_index=_to_int(os.getenv("CAMERA_INDEX"), 0),
            camera_poll_interval_seconds=_to_float(os.getenv("CAMERA_POLL_INTERVAL_SECONDS"), 0.7),
            camera_min_confidence=_to_float(os.getenv("CAMERA_MIN_CONFIDENCE"), 0.85),
            camera_id=os.getenv("CAMERA_ID", "cam-entrada-1"),
        )
