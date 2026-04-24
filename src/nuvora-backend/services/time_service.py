import os
from datetime import datetime
from zoneinfo import ZoneInfo


BUSINESS_TIMEZONE = ZoneInfo(os.getenv("APP_TIMEZONE", "America/Bogota"))


def business_now() -> datetime:
    return datetime.now(BUSINESS_TIMEZONE).replace(tzinfo=None)


def normalize_business_datetime(value: datetime | None) -> datetime:
    if value is None:
        return business_now()
    if value.tzinfo is None:
        return value
    return value.astimezone(BUSINESS_TIMEZONE).replace(tzinfo=None)


def calculate_business_minutes(started_at: datetime, finished_at: datetime | None = None) -> int:
    reference = finished_at or business_now()
    delta = reference - started_at
    return max(0, int(delta.total_seconds() // 60))
