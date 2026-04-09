from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from config.db import SessionLocal
from model.plate_detections import PlateDetection
from schema.plate_detection_schema import PlateDetectionCreate, PlateDetectionResponse, BoundingBox


plate_detection_router = APIRouter(prefix="/plates", tags=["Placas"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@plate_detection_router.post("/", response_model=PlateDetectionResponse)
def create_plate_detection(data: PlateDetectionCreate, db: Session = Depends(get_db)):
    bbox = data.bounding_box

    new_detection = PlateDetection(
        plate=data.plate.strip().upper(),
        plate_confidence=data.plate_confidence,
        detection_confidence=data.detection_confidence,
        region=data.region,
        region_confidence=data.region_confidence,
        bbox_x1=bbox.x1 if bbox else None,
        bbox_y1=bbox.y1 if bbox else None,
        bbox_x2=bbox.x2 if bbox else None,
        bbox_y2=bbox.y2 if bbox else None,
        camera_id=data.camera_id,
        source=data.source,
        detected_at=data.detected_at or datetime.utcnow(),
    )

    db.add(new_detection)
    db.commit()
    db.refresh(new_detection)
    return to_response(new_detection)


@plate_detection_router.get("/", response_model=list[PlateDetectionResponse])
def list_plate_detections(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    rows = db.query(PlateDetection).order_by(PlateDetection.id.desc()).limit(limit).all()
    return [to_response(row) for row in rows]


@plate_detection_router.get("/latest", response_model=PlateDetectionResponse | None)
def latest_plate_detection(db: Session = Depends(get_db)):
    row = db.query(PlateDetection).order_by(PlateDetection.id.desc()).first()
    if not row:
        return None
    return to_response(row)


def to_response(row: PlateDetection) -> PlateDetectionResponse:
    bbox = None
    if row.bbox_x1 is not None and row.bbox_y1 is not None and row.bbox_x2 is not None and row.bbox_y2 is not None:
        bbox = BoundingBox(
            x1=row.bbox_x1,
            y1=row.bbox_y1,
            x2=row.bbox_x2,
            y2=row.bbox_y2,
        )

    return PlateDetectionResponse(
        id=row.id,
        plate=row.plate,
        plate_confidence=float(row.plate_confidence) if row.plate_confidence is not None else None,
        detection_confidence=float(row.detection_confidence) if row.detection_confidence is not None else None,
        region=row.region,
        region_confidence=float(row.region_confidence) if row.region_confidence is not None else None,
        bounding_box=bbox,
        camera_id=row.camera_id,
        source=row.source,
        detected_at=row.detected_at,
        created_at=row.created_at,
    )
