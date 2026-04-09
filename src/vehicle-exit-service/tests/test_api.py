import base64
from datetime import datetime, timezone

import cv2
import numpy as np
from fastapi.testclient import TestClient

from detector import Detection
from main import create_app
from schemas import ExitEventResponse
from settings import ServiceSettings


class FakeDispatcher:
    def __init__(self, result: ExitEventResponse) -> None:
        self.result = result
        self.calls = 0

    def process_event(self, event, strict_forwarding: bool = True):
        self.calls += 1
        return self.result


class FakeFrameDetector:
    def detect(self, frame):
        return [Detection(plate="ABC123", confidence=0.95)]


def _settings() -> ServiceSettings:
    return ServiceSettings(
        service_name="vehicle-exit-service-test",
        backend_exit_url="http://backend:8000/api/events/vehicle-exit",
        backend_api_key="test-key",
        request_timeout_seconds=2.0,
        duplicate_window_seconds=20,
        auto_detection_enabled=False,
        detector_provider="mock",
        camera_index=0,
        camera_poll_interval_seconds=1.0,
        camera_min_confidence=0.9,
        camera_id="cam-test",
    )


def test_health_endpoint() -> None:
    app = create_app(_settings())
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_vehicle_exit_ok() -> None:
    app = create_app(_settings())
    app.state.dispatcher = FakeDispatcher(
        ExitEventResponse(
            accepted=True,
            duplicate=False,
            forwarded=True,
            message="ok",
            plate="ABC123",
            exit_time=datetime(2026, 4, 8, 18, 0, tzinfo=timezone.utc),
        )
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/vehicle-exits",
        json={
            "plate": "abc-123",
            "exit_time": "2026-04-08T18:00:00Z",
            "source": "manual",
        },
    )

    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert app.state.dispatcher.calls == 1


def test_register_vehicle_exit_backend_error() -> None:
    app = create_app(_settings())
    app.state.dispatcher = FakeDispatcher(
        ExitEventResponse(
            accepted=False,
            duplicate=False,
            forwarded=False,
            message="backend error",
            plate="ABC123",
            exit_time=datetime(2026, 4, 8, 18, 0, tzinfo=timezone.utc),
        )
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/vehicle-exits",
        json={
            "plate": "abc123",
            "exit_time": "2026-04-08T18:00:00Z",
            "source": "manual",
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "backend error"


def test_detect_frame_endpoint_registers_event() -> None:
    app = create_app(_settings())
    app.state.dispatcher = FakeDispatcher(
        ExitEventResponse(
            accepted=True,
            duplicate=False,
            forwarded=True,
            message="ok",
            plate="ABC123",
            exit_time=datetime(2026, 4, 8, 18, 0, tzinfo=timezone.utc),
        )
    )
    app.state.frame_detector = FakeFrameDetector()
    client = TestClient(app)

    image = np.zeros((64, 128, 3), dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok is True
    image_b64 = base64.b64encode(encoded.tobytes()).decode("utf-8")

    response = client.post(
        "/api/v1/vehicle-exits/detect-frame",
        json={
            "image_base64": image_b64,
            "camera_id": "cam-test",
        },
    )

    assert response.status_code == 200
    assert response.json()["processed"] == 1
    assert app.state.dispatcher.calls == 1
