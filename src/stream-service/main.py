import json
import os
from pathlib import Path
from typing import Any

import cv2
from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from camera_manager import CameraManager, normalize_source
from stream_generator import generate_mjpeg


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_APP_DIR = Path(__file__).resolve().parent
_load_env_file(_APP_DIR.parent / ".env")
_load_env_file(_APP_DIR / ".env")


class CameraUpsertRequest(BaseModel):
    cam_id: str
    source: int | str


class CameraResponse(BaseModel):
    cam_id: str
    source: int | str
    connected: bool
    frame_count: int
    last_frame_at: str | None = None
    last_error: str | None = None
    width: int | None = None
    height: int | None = None


app = FastAPI(title="Camera Service", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

camera_manager = CameraManager()


def load_configured_cameras() -> list[tuple[str, int | str]]:
    raw_json = os.getenv("CAMERAS_JSON", "").strip()
    cameras: list[tuple[str, int | str]] = []

    if raw_json:
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"CAMERAS_JSON invalido: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError("CAMERAS_JSON debe ser un objeto JSON con formato {cam_id: source}")

        for cam_id, source in data.items():
            cameras.append((str(cam_id), normalize_source(source)))
        return cameras

    if "CAM_INDEX" in os.environ:
        cameras.append(("entrada", normalize_source(os.getenv("CAM_INDEX", "0"))))

    return cameras


def register_camera(cam_id: str, source: int | str, replace: bool = True) -> dict[str, Any]:
    try:
        return camera_manager.add_camera(cam_id, source, replace=replace).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.on_event("startup")
def startup_event():
    for cam_id, source in load_configured_cameras():
        try:
            camera_manager.add_camera(cam_id, source, replace=True)
        except Exception as exc:
            print(f"Error al iniciar camara {cam_id}: {exc}")


@app.on_event("shutdown")
def shutdown_event():
    camera_manager.release()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "camera_count": len(camera_manager.list_statuses()),
    }


@app.get("/cameras", response_model=list[CameraResponse])
def list_cameras():
    return camera_manager.list_statuses()


@app.post("/cameras", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
def create_camera(data: CameraUpsertRequest):
    return register_camera(data.cam_id, data.source, replace=False)


@app.put("/cameras/{cam_id}", response_model=CameraResponse)
def update_camera(cam_id: str, data: CameraUpsertRequest):
    if data.cam_id.strip() != cam_id:
        raise HTTPException(status_code=400, detail="cam_id del path y del body deben coincidir")
    return register_camera(cam_id, data.source, replace=True)


@app.get("/cameras/{cam_id}", response_model=CameraResponse)
def get_camera(cam_id: str):
    try:
        return camera_manager.get_status(cam_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/cameras/{cam_id}")
def delete_camera(cam_id: str):
    try:
        camera_manager.remove_camera(cam_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@app.post("/cameras/{cam_id}/restart", response_model=CameraResponse)
def restart_camera(cam_id: str):
    try:
        return camera_manager.restart_camera(cam_id).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/cameras/{cam_id}/snapshot")
def get_snapshot(cam_id: str):
    try:
        frame = camera_manager.get_frame(cam_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    ok, buffer = cv2.imencode(".jpg", frame)
    if not ok:
        raise HTTPException(status_code=500, detail="No se pudo codificar el snapshot")
    return Response(content=buffer.tobytes(), media_type="image/jpeg")


@app.get("/cameras/{cam_id}/stream")
def get_stream(cam_id: str):
    if not camera_manager.has_camera(cam_id):
        raise HTTPException(status_code=404, detail="Camara no registrada")
    return StreamingResponse(
        generate_mjpeg(camera_manager, cam_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
