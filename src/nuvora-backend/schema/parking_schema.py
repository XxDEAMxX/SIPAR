from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from schema.plate_detection_schema import BoundingBox


Direction = Literal["entry", "exit"]
ProcessingStatus = Literal["processed", "ignored", "error"]


class ParkingDetectionCreate(BaseModel):
    plate: str
    direction: Direction
    plate_confidence: float | None = None
    detection_confidence: float | None = None
    region: str | None = None
    region_confidence: float | None = None
    bounding_box: BoundingBox | None = None
    camera_id: str | None = None
    source: str | None = None
    detected_at: datetime | None = None


class ParkingDetectionResponse(BaseModel):
    detection_id: int
    event_id: int
    ticket_id: int | None = None
    vehicle_id: int | None = None
    plate: str
    direction: Direction
    status: ProcessingStatus
    message: str
    detected_at: datetime
    open_sessions: int
    parking_minutes: int | None = None


class ActiveParkingSession(BaseModel):
    ticket_id: int
    vehicle_id: int
    plate: str
    camera_id: str | None = None
    source: str | None = None
    entered_at: datetime
    parking_minutes: int


class ParkingEventItem(BaseModel):
    event_id: int
    detection_id: int | None = None
    ticket_id: int | None = None
    vehicle_id: int | None = None
    plate: str
    direction: Direction
    status: ProcessingStatus
    message: str
    camera_id: str | None = None
    source: str | None = None
    detected_at: datetime
    parking_minutes: int | None = None


class ParkingStateResponse(BaseModel):
    occupancy: int
    active_sessions: list[ActiveParkingSession]
    recent_events: list[ParkingEventItem]
