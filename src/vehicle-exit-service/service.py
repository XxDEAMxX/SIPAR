from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from threading import Lock

from backend_client import MainBackendClient
from schemas import ExitEventItem, ExitEventRequest, ExitEventResponse


class DuplicateEventGuard:
    def __init__(self, window_seconds: int) -> None:
        self.window = timedelta(seconds=window_seconds)
        self._plates_seen: dict[str, datetime] = {}
        self._lock = Lock()

    def seen_recently(self, plate: str, at_time: datetime) -> bool:
        with self._lock:
            self._evict_old(at_time)
            previous = self._plates_seen.get(plate)
            if previous is None:
                self._plates_seen[plate] = at_time
                return False

            if at_time - previous <= self.window:
                return True

            self._plates_seen[plate] = at_time
            return False

    def _evict_old(self, now: datetime) -> None:
        to_delete = [
            plate for plate, seen_at in self._plates_seen.items() if now - seen_at > self.window
        ]
        for plate in to_delete:
            del self._plates_seen[plate]


class ExitEventRecorder:
    def __init__(self, max_items: int = 100) -> None:
        self._events: deque[ExitEventItem] = deque(maxlen=max_items)
        self._lock = Lock()

    def push(self, item: ExitEventItem) -> None:
        with self._lock:
            self._events.appendleft(item)

    def list_recent(self, limit: int = 30) -> list[ExitEventItem]:
        with self._lock:
            return list(self._events)[:limit]


class ExitEventDispatcher:
    def __init__(
        self,
        backend_client: MainBackendClient,
        duplicate_guard: DuplicateEventGuard,
        event_recorder: ExitEventRecorder | None = None,
    ) -> None:
        self.backend_client = backend_client
        self.duplicate_guard = duplicate_guard
        self.event_recorder = event_recorder

    def _record(self, event: ExitEventRequest, result: ExitEventResponse) -> None:
        if not self.event_recorder:
            return
        self.event_recorder.push(
            ExitEventItem(
                plate=result.plate,
                exit_time=result.exit_time,
                source=event.source,
                confidence=event.confidence,
                forwarded=result.forwarded,
                duplicate=result.duplicate,
                message=result.message,
            )
        )

    def process_event(self, event: ExitEventRequest, strict_forwarding: bool = True) -> ExitEventResponse:
        if self.duplicate_guard.seen_recently(event.plate, event.exit_time):
            response = ExitEventResponse(
                accepted=True,
                duplicate=True,
                forwarded=False,
                message="Evento duplicado omitido por ventana de tiempo",
                plate=event.plate,
                exit_time=event.exit_time,
            )
            self._record(event, response)
            return response

        payload = {
            "placa": event.plate,
            "hora_salida": event.exit_time.isoformat(),
            "fuente": event.source,
            "confianza": event.confidence,
            "camera_id": event.camera_id,
        }

        backend_result = self.backend_client.send_exit_event(payload)
        if backend_result.ok:
            response = ExitEventResponse(
                accepted=True,
                duplicate=False,
                forwarded=True,
                message="Salida registrada y enviada al backend principal",
                plate=event.plate,
                exit_time=event.exit_time,
            )
            self._record(event, response)
            return response

        message = (
            f"No fue posible enviar el evento al backend principal: "
            f"{backend_result.status_code} {backend_result.detail}"
        )
        if strict_forwarding:
            response = ExitEventResponse(
                accepted=False,
                duplicate=False,
                forwarded=False,
                message=message,
                plate=event.plate,
                exit_time=event.exit_time,
            )
            self._record(event, response)
            return response

        response = ExitEventResponse(
            accepted=True,
            duplicate=False,
            forwarded=False,
            message=message,
            plate=event.plate,
            exit_time=event.exit_time,
        )
        self._record(event, response)
        return response
