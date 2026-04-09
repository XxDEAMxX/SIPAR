from datetime import datetime, timezone

from backend_client import BackendResult
from schemas import ExitEventRequest
from service import DuplicateEventGuard, ExitEventDispatcher


class FakeBackendClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def send_exit_event(self, payload: dict) -> BackendResult:
        self.calls.append(payload)
        return BackendResult(ok=True, status_code=200, detail="ok")


def test_dispatcher_forwards_first_event() -> None:
    client = FakeBackendClient()
    dispatcher = ExitEventDispatcher(client, DuplicateEventGuard(window_seconds=10))

    event = ExitEventRequest(
        plate="abc123",
        exit_time=datetime(2026, 4, 8, 17, 30, tzinfo=timezone.utc),
        source="manual",
    )

    result = dispatcher.process_event(event)

    assert result.accepted is True
    assert result.forwarded is True
    assert result.duplicate is False
    assert len(client.calls) == 1
    assert client.calls[0]["placa"] == "ABC123"


def test_dispatcher_skips_duplicate_within_window() -> None:
    client = FakeBackendClient()
    dispatcher = ExitEventDispatcher(client, DuplicateEventGuard(window_seconds=20))

    first = ExitEventRequest(
        plate="ABC123",
        exit_time=datetime(2026, 4, 8, 17, 30, tzinfo=timezone.utc),
        source="manual",
    )
    second = ExitEventRequest(
        plate="ABC123",
        exit_time=datetime(2026, 4, 8, 17, 30, 10, tzinfo=timezone.utc),
        source="auto-camera",
    )

    result_first = dispatcher.process_event(first)
    result_second = dispatcher.process_event(second)

    assert result_first.forwarded is True
    assert result_second.duplicate is True
    assert result_second.forwarded is False
    assert len(client.calls) == 1
