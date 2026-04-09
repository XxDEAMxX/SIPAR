import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
import json

@dataclass
class ParkingSpot:
    id: int
    polygon: np.ndarray  # puntos del ROI
    occupied: bool = False
    plate: str | None = None

class ParkingOccupancyDetector:
    """Detector liviano de cupos — sin GPU requerida."""

    def __init__(self, spots_config: str, method: str = "variance"):
        self.method = method
        self.spots = self._load_spots(spots_config)
        
        if method == "mog2":
            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500, varThreshold=25, detectShadows=True
            )
        elif method == "yolo":
            from ultralytics import YOLO
            self.model = YOLO("yolov8n.pt")  # 6MB, solo CPU

    def _load_spots(self, config_path: str) -> List[ParkingSpot]:
        with open(config_path) as f:
            data = json.load(f)
        return [
            ParkingSpot(id=s["id"], polygon=np.array(s["polygon"], np.int32))
            for s in data["spots"]
        ]

    def _classify_variance(self, roi_gray: np.ndarray, threshold: float = 15.0) -> bool:
        """Varianza de píxeles: baja = libre, alta = ocupado."""
        return float(np.std(roi_gray)) > threshold

    def _classify_mog2(self, frame: np.ndarray, polygon: np.ndarray) -> bool:
        mask = self.bg_subtractor.apply(frame)
        spot_mask = np.zeros(mask.shape, np.uint8)
        cv2.fillPoly(spot_mask, [polygon], 255)
        intersection = cv2.bitwise_and(mask, spot_mask)
        occupied_ratio = np.count_nonzero(intersection) / np.count_nonzero(spot_mask)
        return occupied_ratio > 0.25

    def _classify_yolo(self, frame: np.ndarray, polygon: np.ndarray) -> bool:
        x, y, w, h = cv2.boundingRect(polygon)
        roi = frame[y:y+h, x:x+w]
        results = self.model(roi, classes=[2, 5, 7], verbose=False)  # car, bus, truck
        return len(results[0].boxes) > 0

    def process_frame(self, frame: np.ndarray) -> List[ParkingSpot]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        for spot in self.spots:
            if self.method == "variance":
                mask = np.zeros(gray.shape, np.uint8)
                cv2.fillPoly(mask, [spot.polygon], 255)
                roi = cv2.bitwise_and(gray, gray, mask=mask)
                roi_crop = roi[
                    spot.polygon[:, 1].min():spot.polygon[:, 1].max(),
                    spot.polygon[:, 0].min():spot.polygon[:, 0].max()
                ]
                spot.occupied = self._classify_variance(roi_crop)

            elif self.method == "mog2":
                spot.occupied = self._classify_mog2(frame, spot.polygon)

            elif self.method == "yolo":
                spot.occupied = self._classify_yolo(frame, spot.polygon)

        return self.spots

    def draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        overlay = frame.copy()
        for spot in self.spots:
            color = (0, 0, 220) if spot.occupied else (0, 220, 0)
            cv2.fillPoly(overlay, [spot.polygon], color)
            cx = int(spot.polygon[:, 0].mean())
            cy = int(spot.polygon[:, 1].mean())
            label = f"#{spot.id}"
            if spot.plate:
                label += f" {spot.plate}"
            cv2.putText(overlay, label, (cx - 20, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        return cv2.addWeighted(frame, 0.6, overlay, 0.4, 0)