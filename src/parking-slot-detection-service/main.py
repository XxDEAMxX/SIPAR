import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from slot_detector import build_detector_from_env


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


APP_DIR = Path(__file__).resolve().parent
_load_env_file(APP_DIR.parent / ".env")
_load_env_file(APP_DIR / ".env")

app = FastAPI(title="Parking Slot Detection Service", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

detector = build_detector_from_env(APP_DIR)


@app.on_event("startup")
def startup_event():
    detector.start()


@app.on_event("shutdown")
def shutdown_event():
    detector.stop()


@app.get("/health")
def health():
    state = detector.get_state()
    return {
        "status": "ok",
        "connected": state["connected"],
        "total": state["total"],
        "occupied": state["occupied"],
        "available": state["available"],
        "last_error": state["last_error"],
    }


@app.get("/slots/state")
def get_slots_state():
    return detector.get_state()


@app.post("/slots/reload")
def reload_slots():
    try:
        return detector.reload_slots()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def generate_annotated_stream():
    fps_limit = float(os.getenv("SLOT_STREAM_FPS", "12"))
    frame_interval = 1.0 / fps_limit if fps_limit > 0 else 0.0

    while True:
        try:
            frame_bytes = detector.get_annotated_jpeg()
        except Exception:
            frame_bytes = detector.get_status_jpeg()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )

        if frame_interval > 0:
            time.sleep(frame_interval)


@app.get("/slots/stream")
def get_slots_stream():
    return StreamingResponse(
        generate_annotated_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
