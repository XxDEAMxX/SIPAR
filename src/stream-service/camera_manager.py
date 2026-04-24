from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from threading import Event, Lock, Thread
from typing import Any

import cv2


def normalize_source(source: Any) -> int | str:
    if isinstance(source, int):
        return source
    if isinstance(source, str):
        trimmed = source.strip()
        if trimmed.isdigit():
            return int(trimmed)
        return trimmed
    raise ValueError("El source de la camara debe ser int o str")


@dataclass
class CameraStatus:
    cam_id: str
    source: int | str
    connected: bool
    frame_count: int
    last_frame_at: str | None
    last_error: str | None
    width: int | None
    height: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cam_id": self.cam_id,
            "source": self.source,
            "connected": self.connected,
            "frame_count": self.frame_count,
            "last_frame_at": self.last_frame_at,
            "last_error": self.last_error,
            "width": self.width,
            "height": self.height,
        }


class ManagedCamera:
    def __init__(self, cam_id: str, source: int | str, reconnect_delay_seconds: float = 2.0) -> None:
        self.cam_id = cam_id
        self.source = normalize_source(source)
        self.reconnect_delay_seconds = reconnect_delay_seconds
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._capture = None
        self._capture_lock = Lock()
        self._frame_lock = Lock()
        self._last_frame = None
        self._last_frame_at: str | None = None
        self._last_error: str | None = None
        self._frame_count = 0
        self._connected = False
        self._width: int | None = None
        self._height: int | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._reader_loop, daemon=True, name=f"camera-{self.cam_id}")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        self._release_capture()

    def restart(self) -> None:
        self.stop()
        with self._frame_lock:
            self._last_frame = None
            self._last_frame_at = None
            self._last_error = None
            self._frame_count = 0
            self._connected = False
            self._width = None
            self._height = None
        self.start()

    def get_frame(self):
        with self._frame_lock:
            if self._last_frame is None:
                raise ValueError(f"La camara {self.cam_id} aun no tiene frames disponibles")
            return self._last_frame.copy()

    def status(self) -> CameraStatus:
        with self._frame_lock:
            return CameraStatus(
                cam_id=self.cam_id,
                source=self.source,
                connected=self._connected,
                frame_count=self._frame_count,
                last_frame_at=self._last_frame_at,
                last_error=self._last_error,
                width=self._width,
                height=self._height,
            )

    def _open_capture(self):
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            cap.release()
            raise ValueError(f"No se pudo abrir la camara {self.source}")
        with self._capture_lock:
            self._capture = cap
        with self._frame_lock:
            self._connected = True
            self._last_error = None

    def _release_capture(self) -> None:
        with self._capture_lock:
            cap = self._capture
            self._capture = None
        if cap is not None:
            cap.release()
        with self._frame_lock:
            self._connected = False

    def _mark_error(self, message: str) -> None:
        with self._frame_lock:
            self._connected = False
            self._last_error = message

    def _reader_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._open_capture()
            except Exception as exc:
                self._mark_error(str(exc))
                self._stop_event.wait(self.reconnect_delay_seconds)
                continue

            while not self._stop_event.is_set():
                with self._capture_lock:
                    cap = self._capture
                if cap is None:
                    break

                ok, frame = cap.read()
                if not ok or frame is None:
                    self._mark_error(f"No se pudo leer frame de camara {self.cam_id}")
                    self._release_capture()
                    self._stop_event.wait(self.reconnect_delay_seconds)
                    break

                timestamp = datetime.utcnow().isoformat()
                height, width = frame.shape[:2]
                with self._frame_lock:
                    self._last_frame = frame
                    self._last_frame_at = timestamp
                    self._frame_count += 1
                    self._connected = True
                    self._width = int(width)
                    self._height = int(height)

                time.sleep(0.01)

        self._release_capture()


class CameraManager:
    def __init__(self) -> None:
        self.cameras: dict[str, ManagedCamera] = {}
        self._lock = Lock()

    def add_camera(self, cam_id: str, source: int | str, replace: bool = True) -> CameraStatus:
        normalized_cam_id = cam_id.strip()
        if not normalized_cam_id:
            raise ValueError("cam_id es obligatorio")

        camera = ManagedCamera(normalized_cam_id, source)
        with self._lock:
            existing = self.cameras.get(normalized_cam_id)
            if existing and not replace:
                raise ValueError(f"La camara {normalized_cam_id} ya existe")
            if existing:
                existing.stop()
            self.cameras[normalized_cam_id] = camera
        camera.start()
        return camera.status()

    def remove_camera(self, cam_id: str) -> None:
        with self._lock:
            camera = self.cameras.pop(cam_id, None)
        if camera is None:
            raise ValueError(f"Camara {cam_id} no registrada")
        camera.stop()

    def restart_camera(self, cam_id: str) -> CameraStatus:
        camera = self._get_camera(cam_id)
        camera.restart()
        return camera.status()

    def get_frame(self, cam_id: str):
        return self._get_camera(cam_id).get_frame()

    def get_status(self, cam_id: str) -> dict[str, Any]:
        return self._get_camera(cam_id).status().to_dict()

    def list_statuses(self) -> list[dict[str, Any]]:
        with self._lock:
            cameras = list(self.cameras.values())
        return [camera.status().to_dict() for camera in cameras]

    def has_camera(self, cam_id: str) -> bool:
        with self._lock:
            return cam_id in self.cameras

    def release(self) -> None:
        with self._lock:
            cameras = list(self.cameras.values())
            self.cameras.clear()
        for camera in cameras:
            camera.stop()

    def _get_camera(self, cam_id: str) -> ManagedCamera:
        with self._lock:
            camera = self.cameras.get(cam_id)
        if camera is None:
            raise ValueError(f"Camara {cam_id} no registrada")
        return camera
