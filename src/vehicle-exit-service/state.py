import threading
import time


class PlateDeduplicator:
    def __init__(self, cooldown_seconds: float) -> None:
        self.cooldown_seconds = cooldown_seconds
        self._recent_plates: dict[str, float] = {}
        self._lock = threading.Lock()

    def should_emit(self, plate: str) -> bool:
        now = time.time()
        with self._lock:
            for key, ts in list(self._recent_plates.items()):
                if now - ts > self.cooldown_seconds:
                    del self._recent_plates[key]

            last_seen = self._recent_plates.get(plate)
            if last_seen is not None and now - last_seen < self.cooldown_seconds:
                return False

            self._recent_plates[plate] = now
            return True
