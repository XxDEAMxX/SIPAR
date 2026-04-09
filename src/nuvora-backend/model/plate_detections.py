from sqlalchemy import Column, DateTime, Integer, String, DECIMAL
from sqlalchemy.sql import func

from config.db import Base


class PlateDetection(Base):
    __tablename__ = "placas_detectadas"

    id = Column(Integer, primary_key=True, index=True)
    plate = Column(String(20), nullable=False, index=True)
    plate_confidence = Column(DECIMAL(6, 4), nullable=True)
    detection_confidence = Column(DECIMAL(6, 4), nullable=True)
    region = Column(String(20), nullable=True)
    region_confidence = Column(DECIMAL(6, 4), nullable=True)
    bbox_x1 = Column(Integer, nullable=True)
    bbox_y1 = Column(Integer, nullable=True)
    bbox_x2 = Column(Integer, nullable=True)
    bbox_y2 = Column(Integer, nullable=True)
    camera_id = Column(String(50), nullable=True, index=True)
    source = Column(String(50), nullable=True, default="vehicle-entry-service")
    detected_at = Column(DateTime(timezone=False), nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
