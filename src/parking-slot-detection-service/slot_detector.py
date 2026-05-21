from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any

import cv2
import numpy as np


def normalize_source(source: str) -> int | str:
    trimmed = source.strip()
    if trimmed.isdigit():
        return int(trimmed)
    return trimmed


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ParkingSlotDetector:
    def __init__(
        self,
        source: int | str,
        slots_path: Path,
        base_dir: Path,
        frame_width: int = 800,
        frame_height: int = 600,
        occupied_std_threshold: float = 20.0,
        detection_fps: float = 6.0,
        reconnect_delay_seconds: float = 2.0,
    ) -> None:
        self.source = source
        self.slots_path = slots_path
        self.base_dir = base_dir
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.reference_width = frame_width
        self.reference_height = frame_height
        self.occupied_std_threshold = occupied_std_threshold
        self.detection_fps = detection_fps
        self.reconnect_delay_seconds = reconnect_delay_seconds
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._lock = Lock()
        self._capture = None
        self._static_frame = None
        self._slots: list[dict[str, Any]] = []
        self._slots_mtime: float | None = None
        self._state = self._empty_state(connected=False, last_error="Servicio no iniciado")
        self._annotated_frame = None

    def start(self) -> None:
        self.reload_slots()
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._reader_loop, daemon=True, name="parking-slot-detector")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        self._release_capture()

    def reload_slots(self) -> dict[str, Any]:
        slots = self._load_slots()
        self._slots_mtime = self._get_slots_mtime()
        with self._lock:
            self._slots = slots
            self._state = self._empty_state(
                connected=self._state.get("connected", False),
                last_error=self._state.get("last_error"),
            )
        return self.get_state()

    def maybe_reload_slots(self) -> None:
        current_mtime = self._get_slots_mtime()
        if current_mtime is None or current_mtime == self._slots_mtime:
            return
        slots = self._load_slots()
        with self._lock:
            self._slots = slots
            self._slots_mtime = current_mtime

    def _get_slots_mtime(self) -> float | None:
        if not self.slots_path.exists():
            return None
        return self.slots_path.stat().st_mtime

    def get_state(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._state))

    def get_annotated_jpeg(self) -> bytes:
        with self._lock:
            frame = None if self._annotated_frame is None else self._annotated_frame.copy()

        if frame is None:
            raise ValueError("Aun no hay frames anotados disponibles")

        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            raise ValueError("No se pudo codificar el frame anotado")
        return buffer.tobytes()

    def get_status_jpeg(self) -> bytes:
        state = self.get_state()
        frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
        frame[:] = (18, 24, 38)

        lines = [
            "Servicio de cupos",
            f"Fuente: {state.get('source')}",
            "Esperando frames de la camara...",
        ]
        if state.get("last_error"):
            lines.append(f"Error: {state['last_error']}")

        y = 70
        for index, line in enumerate(lines):
            font_scale = 0.82 if index == 0 else 0.58
            thickness = 2 if index == 0 else 1
            cv2.putText(
                frame,
                str(line)[:105],
                (32, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (255, 255, 255),
                thickness,
                cv2.LINE_AA,
            )
            y += 44

        cv2.putText(
            frame,
            "Verifica que stream-service tenga registrada la camara 'cupos'.",
            (32, self.frame_height - 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (147, 197, 253),
            1,
            cv2.LINE_AA,
        )

        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            raise ValueError("No se pudo codificar el frame de estado")
        return buffer.tobytes()

    def _load_slots(self) -> list[dict[str, Any]]:
        if not self.slots_path.exists():
            raise FileNotFoundError(f"No existe el archivo de cupos: {self.slots_path}")

        data = json.loads(self.slots_path.read_text(encoding="utf-8"))
        frame_meta = data.get("frame") or {}
        self.reference_width = int(frame_meta.get("width") or self.frame_width)
        self.reference_height = int(frame_meta.get("height") or self.frame_height)
        slots = data.get("spots", [])
        if not isinstance(slots, list):
            raise ValueError("El archivo de cupos debe tener una lista 'spots'")

        normalized_slots: list[dict[str, Any]] = []
        for index, slot in enumerate(slots, start=1):
            polygon = slot.get("polygon")
            if not isinstance(polygon, list) or len(polygon) < 3:
                raise ValueError(f"Cupo invalido en posicion {index}: polygon requiere minimo 3 puntos")
            normalized_slots.append(
                {
                    "id": slot.get("id", index),
                    "polygon": [[int(point[0]), int(point[1])] for point in polygon],
                }
            )
        return normalized_slots

    def _empty_state(self, connected: bool, last_error: str | None = None) -> dict[str, Any]:
        slots = [
            {
                "id": slot["id"],
                "occupied": False,
                "confidence": 0.0,
                "stddev": 0.0,
                "polygon": slot["polygon"],
            }
            for slot in self._slots
        ]
        return {
            "source": self.source,
            "connected": connected,
            "updated_at": None,
            "total": len(slots),
            "occupied": 0,
            "available": len(slots),
            "last_error": last_error,
            "slots": slots,
        }

    def _reader_loop(self) -> None:
        frame_interval = 1.0 / self.detection_fps if self.detection_fps > 0 else 0.0

        while not self._stop_event.is_set():
            try:
                self._open_capture()
            except Exception as exc:
                self._mark_disconnected(str(exc))
                self._stop_event.wait(self.reconnect_delay_seconds)
                continue

            while not self._stop_event.is_set():
                self.maybe_reload_slots()
                ok, frame = self._read_frame()
                if not ok or frame is None:
                    self._mark_disconnected("No se pudo leer frame de la camara de cupos")
                    self._release_capture()
                    self._stop_event.wait(self.reconnect_delay_seconds)
                    break

                frame = cv2.resize(frame, (self.frame_width, self.frame_height))
                state, annotated = self._analyze_frame(frame)
                with self._lock:
                    self._state = state
                    self._annotated_frame = annotated

                if frame_interval > 0:
                    self._stop_event.wait(frame_interval)

        self._release_capture()

    def _open_capture(self) -> None:
        static_frame = self._load_static_image()
        if static_frame is not None:
            self._static_frame = static_frame
            with self._lock:
                self._state["connected"] = True
                self._state["last_error"] = None
            return

        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            cap.release()
            raise ValueError(f"No se pudo abrir la camara de cupos: {self.source}")
        self._capture = cap
        with self._lock:
            self._state["connected"] = True
            self._state["last_error"] = None

    def _release_capture(self) -> None:
        cap = self._capture
        self._capture = None
        self._static_frame = None
        if cap is not None:
            cap.release()

    def _read_frame(self):
        if self._static_frame is not None:
            return True, self._static_frame.copy()
        if self._capture is None:
            return False, None
        return self._capture.read()

    def _load_static_image(self):
        if not isinstance(self.source, str):
            return None

        source_path = Path(self.source)
        if not source_path.is_absolute():
            source_path = self.base_dir / source_path
        source_path = source_path.resolve()

        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        if source_path.suffix.lower() not in image_extensions:
            return None
        if not source_path.exists():
            raise ValueError(f"No existe la imagen de cupos: {source_path}")

        frame = cv2.imread(str(source_path))
        if frame is None:
            raise ValueError(f"No se pudo leer la imagen de cupos: {source_path}")
        return frame

    def _mark_disconnected(self, message: str) -> None:
        with self._lock:
            self._state["connected"] = False
            self._state["last_error"] = message

    def _analyze_frame(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        analysis_height, analysis_width = gray.shape[:2]
        slot_states = []
        occupied_count = 0

        for slot in self._slots:
            polygon = self._scale_polygon(slot["polygon"], analysis_width, analysis_height)
            stddev = self._slot_stddev(gray, polygon)
            occupied = stddev >= self.occupied_std_threshold
            confidence = self._confidence_from_stddev(stddev)
            if occupied:
                occupied_count += 1
            slot_states.append(
                {
                    "id": slot["id"],
                    "occupied": occupied,
                    "confidence": confidence,
                    "stddev": round(stddev, 2),
                    "polygon": polygon,
                }
            )

        total = len(slot_states)
        state = {
            "source": self.source,
            "connected": True,
            "updated_at": utc_now(),
            "total": total,
            "occupied": occupied_count,
            "available": max(total - occupied_count, 0),
            "last_error": None,
            "slots": slot_states,
        }
        return state, self._draw_slots(frame, slot_states, state)

    def _scale_polygon(self, polygon: list[list[int]], target_width: int, target_height: int) -> list[list[int]]:
        if self.reference_width <= 0 or self.reference_height <= 0:
            return polygon

        scale_x = target_width / self.reference_width
        scale_y = target_height / self.reference_height
        return [
            [
                int(round(point[0] * scale_x)),
                int(round(point[1] * scale_y)),
            ]
            for point in polygon
        ]

    def _slot_stddev(self, gray, polygon: list[list[int]]) -> float:
        mask = np.zeros(gray.shape, np.uint8)
        points = np.array(polygon, np.int32)
        cv2.fillPoly(mask, [points], 255)
        pixels = gray[mask == 255]
        if pixels.size == 0:
            return 0.0
        return float(np.std(pixels))

    def _confidence_from_stddev(self, stddev: float) -> float:
        if self.occupied_std_threshold <= 0:
            return 1.0
        return round(min(stddev / self.occupied_std_threshold, 1.0), 3)

    def _draw_slots(self, frame, slot_states: list[dict[str, Any]], state: dict[str, Any]):
        overlay = frame.copy()

        for slot in slot_states:
            points = np.array(slot["polygon"], np.int32)
            color = (0, 0, 220) if slot["occupied"] else (0, 180, 0)
            cv2.fillPoly(overlay, [points], color)

        annotated = cv2.addWeighted(frame, 0.62, overlay, 0.38, 0)

        for slot in slot_states:
            points = np.array(slot["polygon"], np.int32)
            color = (0, 0, 220) if slot["occupied"] else (0, 180, 0)
            cv2.polylines(annotated, [points], True, color, 2)
            center_x = int(np.mean([point[0] for point in slot["polygon"]]))
            center_y = int(np.mean([point[1] for point in slot["polygon"]]))
            cv2.putText(
                annotated,
                str(slot["id"]),
                (center_x - 8, center_y + 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                2,
            )

        cv2.putText(
            annotated,
            f"Libres: {state['available']}  Ocupados: {state['occupied']}",
            (14, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.78,
            (255, 255, 255),
            2,
        )
        return annotated


def build_detector_from_env(base_dir: Path) -> ParkingSlotDetector:
    default_slots_path = base_dir.parent / "test-deteccion" / "cupos.json"
    source = normalize_source(os.getenv("SLOT_CAMERA_SOURCE", "http://127.0.0.1:8010/cameras/cupos/stream"))
    raw_slots_path = Path(os.getenv("SLOTS_CONFIG_PATH", str(default_slots_path)))
    slots_path = raw_slots_path if raw_slots_path.is_absolute() else base_dir / raw_slots_path
    return ParkingSlotDetector(
        source=source,
        slots_path=slots_path.resolve(),
        base_dir=base_dir,
        frame_width=int(os.getenv("SLOT_FRAME_WIDTH", "800")),
        frame_height=int(os.getenv("SLOT_FRAME_HEIGHT", "600")),
        occupied_std_threshold=float(os.getenv("SLOT_OCCUPIED_STD_THRESHOLD", "20")),
        detection_fps=float(os.getenv("SLOT_DETECTION_FPS", "6")),
        reconnect_delay_seconds=float(os.getenv("SLOT_RECONNECT_DELAY_SECONDS", "2")),
    )
