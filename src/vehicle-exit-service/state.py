import threading
import time
from dataclasses import dataclass, field


class PlateDeduplicator:
    def __init__(self, cooldown_seconds: float) -> None:
        self.cooldown_seconds = cooldown_seconds
        self._recent_plates: dict[str, float] = {}
        self._lock = threading.Lock()

    def should_emit(self, plate: str) -> bool:
        canonical_plate = canonicalize_plate(plate)
        now = time.time()
        with self._lock:
            for key, ts in list(self._recent_plates.items()):
                if now - ts > self.cooldown_seconds:
                    del self._recent_plates[key]

            last_seen = self._recent_plates.get(canonical_plate)
            if last_seen is not None and now - last_seen < self.cooldown_seconds:
                return False

            self._recent_plates[canonical_plate] = now
            return True


AMBIGUOUS_CANONICAL_MAP = {
    "0": "0",
    "O": "0",
    "Q": "0",
    "D": "0",
    "1": "1",
    "I": "1",
    "L": "1",
    "2": "2",
    "Z": "2",
    "5": "5",
    "S": "5",
    "6": "6",
    "G": "6",
    "7": "7",
    "T": "7",
    "8": "8",
    "B": "8",
}


def sanitize_plate(plate: str) -> str:
    return "".join(ch for ch in (plate or "").upper() if ch.isalnum())


def canonicalize_plate(plate: str) -> str:
    sanitized = sanitize_plate(plate)
    return "".join(AMBIGUOUS_CANONICAL_MAP.get(ch, ch) for ch in sanitized)


def is_plausible_plate(plate: str) -> bool:
    return len(sanitize_plate(plate)) == 6


@dataclass
class PlateObservation:
    plate: str
    confidence: float
    observed_at: float


@dataclass
class PlateSession:
    first_seen: float
    last_seen: float
    observations: list[PlateObservation] = field(default_factory=list)


@dataclass(frozen=True)
class ConsensusPlate:
    plate: str
    confidence: float
    observation_count: int
    support_count: int
    first_seen: float
    last_seen: float


class PlateConsensusBuffer:
    def __init__(
        self,
        window_seconds: float,
        min_observations: int,
        max_plate_length: int = 8,
    ) -> None:
        self.window_seconds = window_seconds
        self.min_observations = min_observations
        self.max_plate_length = max_plate_length
        self._lock = threading.Lock()
        self._session: PlateSession | None = None

    def add_observation(
        self,
        plate: str,
        confidence: float | None,
        observed_at: float | None = None,
    ) -> None:
        sanitized = sanitize_plate(plate)
        if not sanitized or len(sanitized) > self.max_plate_length:
            return

        now = observed_at if observed_at is not None else time.time()
        observation = PlateObservation(
            plate=sanitized,
            confidence=confidence if confidence is not None else 0.0,
            observed_at=now,
        )
        with self._lock:
            if self._session is None:
                self._session = PlateSession(first_seen=now, last_seen=now)
            self._session.last_seen = now
            self._session.observations.append(observation)

    def flush_ready(self, observed_at: float | None = None) -> list[ConsensusPlate]:
        now = observed_at if observed_at is not None else time.time()
        with self._lock:
            session = self._session
            if session is None:
                return []
            if now - session.last_seen < self.window_seconds:
                return []
            self._session = None

        consensus = self._build_consensus(session)
        return [consensus] if consensus is not None else []

    def clear(self) -> None:
        with self._lock:
            self._session = None

    def _build_consensus(self, session: PlateSession) -> ConsensusPlate | None:
        if len(session.observations) < self.min_observations:
            return None

        canonical_stats: dict[str, dict[str, float | dict[str, dict[str, float]]]] = {}
        for observation in session.observations:
            canonical_plate = canonicalize_plate(observation.plate)
            data = canonical_stats.setdefault(
                canonical_plate,
                {"count": 0.0, "confidence_sum": 0.0, "last_seen": 0.0},
            )
            data["count"] += 1
            data["confidence_sum"] += observation.confidence
            data["last_seen"] = max(data["last_seen"], observation.observed_at)
            variants = data.setdefault("variants", {})
            variant = variants.setdefault(
                observation.plate,
                {"count": 0.0, "confidence_sum": 0.0, "last_seen": 0.0},
            )
            variant["count"] += 1
            variant["confidence_sum"] += observation.confidence
            variant["last_seen"] = max(variant["last_seen"], observation.observed_at)

        _, best_canonical_data = max(
            canonical_stats.items(),
            key=lambda item: (
                item[1]["count"],
                item[1]["confidence_sum"],
                item[1]["last_seen"],
                item[0],
            ),
        )
        variants = best_canonical_data["variants"]
        best_plate, best_data = max(
            variants.items(),
            key=lambda item: (
                item[1]["count"],
                item[1]["confidence_sum"],
                item[1]["last_seen"],
                item[0],
            ),
        )
        avg_confidence = best_data["confidence_sum"] / best_data["count"]
        return ConsensusPlate(
            plate=best_plate,
            confidence=avg_confidence,
            observation_count=int(best_data["count"]),
            support_count=int(best_canonical_data["count"]),
            first_seen=session.first_seen,
            last_seen=session.last_seen,
        )


class PlatePresenceTracker:
    def __init__(self, reset_after_seconds: float) -> None:
        self.reset_after_seconds = reset_after_seconds
        self._lock = threading.Lock()
        self._last_seen: dict[str, float] = {}
        self._active_emitted: set[str] = set()

    def note_seen(self, plate: str, observed_at: float | None = None) -> None:
        canonical_plate = canonicalize_plate(plate)
        now = observed_at if observed_at is not None else time.time()
        with self._lock:
            self._last_seen[canonical_plate] = now
            self._cleanup_locked(now)

    def can_emit(self, plate: str, observed_at: float | None = None) -> bool:
        canonical_plate = canonicalize_plate(plate)
        now = observed_at if observed_at is not None else time.time()
        with self._lock:
            self._cleanup_locked(now)
            return canonical_plate not in self._active_emitted

    def mark_emitted(self, plate: str, observed_at: float | None = None) -> None:
        canonical_plate = canonicalize_plate(plate)
        now = observed_at if observed_at is not None else time.time()
        with self._lock:
            self._last_seen[canonical_plate] = now
            self._active_emitted.add(canonical_plate)
            self._cleanup_locked(now)

    def _cleanup_locked(self, now: float) -> None:
        for canonical_plate in list(self._active_emitted):
            last_seen = self._last_seen.get(canonical_plate, 0.0)
            if now - last_seen > self.reset_after_seconds:
                self._active_emitted.remove(canonical_plate)
