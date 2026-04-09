from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from threading import Lock

from backend_client import MainBackendClient
from schemas import EntryEventItem, EntryEventRequest, EntryEventResponse


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


class EntryEventRecorder:
    def __init__(self, max_items: int = 100) -> None:
        self._events: deque[EntryEventItem] = deque(maxlen=max_items)
        self._lock = Lock()

    def push(self, item: EntryEventItem) -> None:
        with self._lock:
            self._events.appendleft(item)

    def list_recent(self, limit: int = 30) -> list[EntryEventItem]:
        with self._lock:
            return list(self._events)[:limit]


class EntryEventDispatcher:
    def __init__(
        self,
        backend_client: MainBackendClient,
        duplicate_guard: DuplicateEventGuard,
        event_recorder: EntryEventRecorder | None = None,
    ) -> None:
        self.backend_client = backend_client
        self.duplicate_guard = duplicate_guard
        self.event_recorder = event_recorder

    def _record(self, event: EntryEventRequest, result: EntryEventResponse) -> None:
        if not self.event_recorder:
            return
        self.event_recorder.push(
            EntryEventItem(
                plate=result.plate,
                entry_time=result.entry_time,
                source=event.source,
                confidence=event.confidence,
                forwarded=result.forwarded,
                duplicate=result.duplicate,
                message=result.message,
            )
        )

    def process_event(self, event: EntryEventRequest, strict_forwarding: bool = True) -> EntryEventResponse:
        if self.duplicate_guard.seen_recently(event.plate, event.entry_time):
            response = EntryEventResponse(
                accepted=True,
                duplicate=True,
                forwarded=False,
                message="Evento duplicado omitido por ventana de tiempo",
                plate=event.plate,
                entry_time=event.entry_time,
            )
            self._record(event, response)
            return response

        payload = {
            "placa": event.plate,
            "hora_entrada": event.entry_time.isoformat(),
            "fuente": event.source,
            "confianza": event.confidence,
            "camera_id": event.camera_id,
        }

        backend_result = self.backend_client.send_entry_event(payload)
        if backend_result.ok:
            response = EntryEventResponse(
                accepted=True,
                duplicate=False,
                forwarded=True,
                message="Entrada registrada y enviada al backend principal",
                plate=event.plate,
                entry_time=event.entry_time,
            )
            self._record(event, response)
            return response

        message = (
            f"No fue posible enviar el evento al backend principal: "
            f"{backend_result.status_code} {backend_result.detail}"
        )
        if strict_forwarding:
            response = EntryEventResponse(
                accepted=False,
                duplicate=False,
                forwarded=False,
                message=message,
                plate=event.plate,
                entry_time=event.entry_time,
            )
            self._record(event, response)
            return response

        response = EntryEventResponse(
            accepted=True,
            duplicate=False,
            forwarded=False,
            message=message,
            plate=event.plate,
            entry_time=event.entry_time,
        )
        self._record(event, response)
        return response
