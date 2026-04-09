from datetime import datetime

from pydantic import BaseModel


class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int


class PlateDetectionCreate(BaseModel):
    plate: str
    plate_confidence: float | None = None
    detection_confidence: float | None = None
    region: str | None = None
    region_confidence: float | None = None
    bounding_box: BoundingBox | None = None
    camera_id: str | None = None
    source: str | None = "vehicle-entry-service"
    detected_at: datetime | None = None


class PlateDetectionResponse(BaseModel):
    id: int
    plate: str
    plate_confidence: float | None = None
    detection_confidence: float | None = None
    region: str | None = None
    region_confidence: float | None = None
    bounding_box: BoundingBox | None = None
    camera_id: str | None = None
    source: str | None = None
    detected_at: datetime
    created_at: datetime | None = None

    class Config:
        from_attributes = True
