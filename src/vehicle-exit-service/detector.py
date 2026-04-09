from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    plate: str
    confidence: float


class BaseDetector:
    def detect(self, frame: Any) -> list[Detection]:
        raise NotImplementedError


class MockDetector(BaseDetector):
    def __init__(self, mock_file: str | None = None) -> None:
        self._queue: list[Detection] = []
        if mock_file:
            self._load_file(mock_file)

    def _load_file(self, mock_file: str) -> None:
        path = Path(mock_file)
        if not path.exists():
            logger.warning("Archivo de mock no encontrado: %s", mock_file)
            return

        with path.open("r", encoding="utf-8") as fh:
            rows = json.load(fh)
            for row in rows:
                plate = str(row.get("plate", "")).replace("-", "").replace(" ", "").upper()
                confidence = float(row.get("confidence", 1.0))
                if plate:
                    self._queue.append(Detection(plate=plate, confidence=confidence))

    def detect(self, frame: Any) -> list[Detection]:
        if not self._queue:
            return []
        return [self._queue.pop(0)]


class FastAlprDetector(BaseDetector):
    def __init__(self) -> None:
        from fast_alpr import ALPR

        self._alpr = ALPR(
            detector_model="yolo-v9-t-384-license-plate-end2end",
            ocr_model="cct-xs-v1-global-model",
        )

    def detect(self, frame: Any) -> list[Detection]:
        detections: list[Detection] = []

        raw = None
        for method in ("predict", "recognize", "run"):
            fn = getattr(self._alpr, method, None)
            if callable(fn):
                raw = fn(frame)
                break

        if raw is None and hasattr(self._alpr, "draw_predictions"):
            rendered = self._alpr.draw_predictions(frame)
            raw = getattr(rendered, "predictions", None)

        for plate, confidence in _extract_plates(raw):
            normalized = plate.replace("-", "").replace(" ", "").upper()
            if normalized:
                detections.append(Detection(plate=normalized, confidence=confidence))

        return detections


def _extract_plates(payload: Any) -> list[tuple[str, float]]:
    found: list[tuple[str, float]] = []

    def _walk(node: Any) -> None:
        if node is None:
            return

        if isinstance(node, dict):
            plate_value = _find_value(node, ["plate", "text", "license", "number"])
            conf_value = _find_value(node, ["confidence", "score", "probability"])
            if isinstance(plate_value, str):
                confidence = float(conf_value) if isinstance(conf_value, (float, int, str)) else 1.0
                found.append((plate_value, confidence))
            for value in node.values():
                _walk(value)
            return

        if isinstance(node, (list, tuple, set)):
            for item in node:
                _walk(item)
            return

        if hasattr(node, "__dict__"):
            _walk(vars(node))

    _walk(payload)

    unique: dict[str, float] = {}
    for plate, confidence in found:
        if plate not in unique or confidence > unique[plate]:
            unique[plate] = confidence

    return [(plate, conf) for plate, conf in unique.items()]


def _find_value(data: dict, keys: list[str]) -> Any:
    lowered = {str(k).lower(): v for k, v in data.items()}
    for key in keys:
        if key in lowered:
            return lowered[key]
    return None


def build_detector(provider: str, mock_file: str | None = None) -> BaseDetector:
    provider = provider.lower().strip()
    if provider == "fast-alpr":
        try:
            return FastAlprDetector()
        except Exception as exc:  # pragma: no cover
            logger.exception("No se pudo inicializar fast-alpr, se usa detector mock: %s", exc)
            return MockDetector(mock_file=mock_file)

    return MockDetector(mock_file=mock_file)
