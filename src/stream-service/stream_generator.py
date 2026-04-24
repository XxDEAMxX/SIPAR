import time

import cv2


def generate_mjpeg(manager, cam_id: str, fps_limit: float = 120.0):
    frame_interval = 1.0 / fps_limit if fps_limit > 0 else 0.0

    while manager.has_camera(cam_id):
        try:
            frame = manager.get_frame(cam_id)
        except Exception:
            time.sleep(0.1)
            continue

        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            time.sleep(0.05)
            continue

        frame_bytes = buffer.tobytes()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )

        if frame_interval > 0:
            time.sleep(frame_interval)
