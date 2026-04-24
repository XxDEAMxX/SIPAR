import logging
import time
from datetime import datetime, timezone
from typing import Any

import onnxruntime as ort
from fast_alpr import ALPR

from backend import BackendClient
from config import Settings
from state import PlateConsensusBuffer, PlateDeduplicator, PlatePresenceTracker, is_plausible_plate


logger = logging.getLogger("vehicle-exit-service")


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
        consensus_buffer: PlateConsensusBuffer,
        presence_tracker: PlatePresenceTracker,
        backend_client: BackendClient,
    ) -> None:
        self.settings = settings
        self.deduplicator = deduplicator
        self.consensus_buffer = consensus_buffer
        self.presence_tracker = presence_tracker
        self.backend_client = backend_client
        self._immediate_plate: str | None = None
        self._immediate_hits = 0
        self._emit_locked_until = 0.0

    def _reset_immediate_candidate(self) -> None:
        self._immediate_plate = None
        self._immediate_hits = 0

    def _is_emit_locked(self) -> bool:
        return time.time() < self._emit_locked_until

    def _emit_detection(
        self,
        plate: str,
        confidence: float,
        observation_count: int,
        mode: str,
    ) -> None:
        if not is_plausible_plate(plate):
            return
        if not self.presence_tracker.can_emit(plate):
            return
        if not self.deduplicator.should_emit(plate):
            return

        conf_text = f"{confidence:.3f}"
        print(
            f"Placa {mode}: {plate} | confianza={conf_text} | observaciones={observation_count}",
            flush=True,
        )

        payload = {
            "plate": plate,
            "plate_confidence": confidence,
            "direction": self.settings.detection_direction,
            "detection_confidence": confidence,
            "camera_id": self.settings.camera_id,
            "source": self.settings.source_name,
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }
        self.backend_client.send_detection(payload)
        self.presence_tracker.mark_emitted(plate)
        self._emit_locked_until = time.time() + self.settings.post_emit_lock_seconds
        self.consensus_buffer.clear()
        self._reset_immediate_candidate()

    def handle_result(self, result: Any) -> None:
        if self._is_emit_locked():
            return

        ocr = getattr(result, "ocr", None)
        detection = getattr(result, "detection", None)
        if ocr is None:
            return

        plate = (getattr(ocr, "text", "") or "").strip().upper()
        if not plate:
            return
        if not is_plausible_plate(plate):
            self._reset_immediate_candidate()
            return

        self.presence_tracker.note_seen(plate)

        detection_confidence = normalize_confidence(
            getattr(detection, "confidence", None)
        )
        if (
            detection_confidence is not None
            and detection_confidence < self.settings.min_detection_confidence
        ):
            return

        plate_confidence = normalize_confidence(getattr(ocr, "confidence", None))
        if (
            plate_confidence is not None
            and plate_confidence < self.settings.min_plate_confidence
        ):
            self._reset_immediate_candidate()
            return
        if (
            plate_confidence is not None
            and plate_confidence >= self.settings.immediate_emit_plate_confidence
        ):
            if self._immediate_plate == plate:
                self._immediate_hits += 1
            else:
                self._immediate_plate = plate
                self._immediate_hits = 1

            if self._immediate_hits >= self.settings.immediate_emit_min_hits:
                self._emit_detection(
                    plate=plate,
                    confidence=plate_confidence,
                    observation_count=self._immediate_hits,
                    mode="inmediata",
                )
            return
        self._reset_immediate_candidate()
        consensus_confidence = plate_confidence
        if consensus_confidence is None:
            consensus_confidence = detection_confidence

        self.consensus_buffer.add_observation(plate, consensus_confidence)

    def flush_pending(self) -> None:
        if self._is_emit_locked():
            self.consensus_buffer.clear()
            return

        for consensus in self.consensus_buffer.flush_ready():
            if not is_plausible_plate(consensus.plate):
                continue
            if consensus.observation_count < self.settings.consensus_min_observations:
                continue
            if consensus.support_count < self.settings.consensus_min_support:
                continue
            if consensus.confidence < self.settings.consensus_min_confidence:
                continue
            self._emit_detection(
                plate=consensus.plate,
                confidence=consensus.confidence,
                observation_count=consensus.observation_count,
                mode="consolidada",
            )
