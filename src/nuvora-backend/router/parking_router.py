import json
from datetime import datetime, timezone
from decimal import Decimal
from queue import Empty, Full, Queue
from threading import Lock

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config.auth import verify_service_api_key
from config.db import SessionLocal
from model.parking_events import ParkingEvent
from model.plate_detections import PlateDetection
from model.tickets import Ticket
from model.vehiculos import Vehiculo
from services.plate_resolution import resolve_plate
from schema.parking_schema import (
    ActiveParkingSession,
    ParkingDetectionCreate,
    ParkingDetectionResponse,
    ParkingEventItem,
    ParkingStateResponse,
)


parking_router = APIRouter(prefix="/parking", tags=["Parqueadero"])


class EventBroker:
    def __init__(self) -> None:
        self._lock = Lock()
        self._subscribers: list[Queue] = []

    def subscribe(self) -> Queue:
        queue: Queue = Queue(maxsize=100)
        with self._lock:
            self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: Queue) -> None:
        with self._lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)

    def publish(self, event: dict) -> None:
        with self._lock:
            subscribers = list(self._subscribers)

        for queue in subscribers:
            try:
                queue.put_nowait(event)
            except Full:
                try:
                    queue.get_nowait()
                except Empty:
                    pass
                try:
                    queue.put_nowait(event)
                except Full:
                    continue


broker = EventBroker()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def normalize_detected_at(value: datetime | None) -> datetime:
    if value is None:
        return datetime.utcnow()
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def calculate_minutes(started_at: datetime, finished_at: datetime | None = None) -> int:
    reference = finished_at or datetime.utcnow()
    delta = reference - started_at
    return max(0, int(delta.total_seconds() // 60))


def get_open_ticket(db: Session, vehicle_id: int) -> Ticket | None:
    return (
        db.query(Ticket)
        .filter(Ticket.vehiculo_id == vehicle_id, Ticket.estado == "abierto")
        .order_by(Ticket.hora_entrada.desc())
        .first()
    )


def get_preferred_known_plates(db: Session, candidate_plates: tuple[str, ...]) -> list[str]:
    if not candidate_plates:
        return []

    open_ticket_rows = (
        db.query(Vehiculo.placa)
        .join(Ticket, Ticket.vehiculo_id == Vehiculo.id)
        .filter(Ticket.estado == "abierto", Vehiculo.placa.in_(candidate_plates))
        .all()
    )
    known_vehicle_rows = db.query(Vehiculo.placa).filter(Vehiculo.placa.in_(candidate_plates)).all()

    preferred: list[str] = []
    for row in open_ticket_rows + known_vehicle_rows:
        plate = row[0]
        if plate not in preferred:
            preferred.append(plate)
    return preferred


def build_event_payload(event: ParkingEvent, parking_minutes: int | None) -> ParkingEventItem:
    return ParkingEventItem(
        event_id=event.id,
        detection_id=event.detection_id,
        ticket_id=event.ticket_id,
        vehicle_id=event.vehiculo_id,
        plate=event.plate,
        direction=event.direction,
        status=event.status,
        message=event.message,
        camera_id=event.camera_id,
        source=event.source,
        detected_at=event.detected_at,
        parking_minutes=parking_minutes,
    )


@parking_router.post("/detections", response_model=ParkingDetectionResponse, dependencies=[Depends(verify_service_api_key)])
def process_detection(data: ParkingDetectionCreate, db: Session = Depends(get_db)):
    detected_at = normalize_detected_at(data.detected_at)
    initial_resolution = resolve_plate(data.plate)
    raw_plate = initial_resolution.raw_plate or data.plate.strip().upper()
    preferred_plates = get_preferred_known_plates(
        db,
        tuple(candidate.plate for candidate in initial_resolution.candidates),
    )
    has_exact_candidate = any(candidate.corrections == 0 for candidate in initial_resolution.candidates)
    context_plates = preferred_plates if data.direction == "exit" or not has_exact_candidate else []
    resolution = resolve_plate(data.plate, context_plates)
    normalized_plate = resolution.resolved_plate or raw_plate
    bbox = data.bounding_box

    detection = PlateDetection(
        plate=raw_plate,
        plate_confidence=data.plate_confidence,
        detection_confidence=data.detection_confidence,
        region=data.region,
        region_confidence=data.region_confidence,
        bbox_x1=bbox.x1 if bbox else None,
        bbox_y1=bbox.y1 if bbox else None,
        bbox_x2=bbox.x2 if bbox else None,
        bbox_y2=bbox.y2 if bbox else None,
        camera_id=data.camera_id,
        source=data.source or f"vehicle-{data.direction}-service",
        detected_at=detected_at,
    )
    db.add(detection)
    db.flush()

    if resolution.resolved_plate is None:
        event = ParkingEvent(
            vehiculo_id=None,
            ticket_id=None,
            detection_id=detection.id,
            plate=raw_plate,
            direction=data.direction,
            status="ignored",
            message=resolution.reason or "La detección fue descartada.",
            camera_id=data.camera_id,
            source=data.source or f"vehicle-{data.direction}-service",
            detected_at=detected_at,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        open_sessions = db.query(Ticket).filter(Ticket.estado == "abierto").count()
        event_payload = build_event_payload(event, parking_minutes=None)
        broker.publish(
            {
                "type": "parking_event",
                "event": event_payload.model_dump(mode="json"),
                "open_sessions": open_sessions,
            }
        )

        return ParkingDetectionResponse(
            detection_id=detection.id,
            event_id=event.id,
            ticket_id=None,
            vehicle_id=None,
            plate=raw_plate,
            direction=data.direction,
            status="ignored",
            message=event.message,
            detected_at=detected_at,
            open_sessions=open_sessions,
            parking_minutes=None,
        )

    vehicle = db.query(Vehiculo).filter(Vehiculo.placa == normalized_plate).first()
    if vehicle is None:
        vehicle = Vehiculo(placa=normalized_plate)
        db.add(vehicle)
        db.flush()

    ticket = get_open_ticket(db, vehicle.id)
    parking_minutes: int | None = None

    if data.direction == "entry":
        if ticket:
            status = "ignored"
            message = "La placa ya tiene una entrada activa."
            parking_minutes = calculate_minutes(ticket.hora_entrada, detected_at)
        else:
            ticket = Ticket(
                vehiculo_id=vehicle.id,
                hora_entrada=detected_at,
                estado="abierto",
            )
            db.add(ticket)
            db.flush()
            status = "processed"
            message = "Entrada registrada correctamente."
    else:
        if ticket is None:
            status = "ignored"
            message = "No existe una entrada activa para esta placa."
        else:
            ticket.hora_salida = detected_at
            ticket.estado = "cerrado"
            ticket.monto_total = Decimal("0.00")
            parking_minutes = calculate_minutes(ticket.hora_entrada, detected_at)
            status = "processed"
            message = "Salida registrada correctamente."

    if resolution.corrections:
        if status == "processed":
            message = f"{message[:-1]} como {normalized_plate}."
        else:
            message = f"Se asume la placa {normalized_plate}. {message}"

    event = ParkingEvent(
        vehiculo_id=vehicle.id,
        ticket_id=ticket.id if ticket else None,
        detection_id=detection.id,
        plate=normalized_plate,
        direction=data.direction,
        status=status,
        message=message,
        camera_id=data.camera_id,
        source=data.source or f"vehicle-{data.direction}-service",
        detected_at=detected_at,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    open_sessions = db.query(Ticket).filter(Ticket.estado == "abierto").count()
    event_payload = build_event_payload(event, parking_minutes=parking_minutes)
    broker.publish(
        {
            "type": "parking_event",
            "event": event_payload.model_dump(mode="json"),
            "open_sessions": open_sessions,
        }
    )

    return ParkingDetectionResponse(
        detection_id=detection.id,
        event_id=event.id,
        ticket_id=ticket.id if ticket else None,
        vehicle_id=vehicle.id,
        plate=normalized_plate,
        direction=data.direction,
        status=status,
        message=message,
        detected_at=detected_at,
        open_sessions=open_sessions,
        parking_minutes=parking_minutes,
    )


@parking_router.get("/state", response_model=ParkingStateResponse)
def get_parking_state(db: Session = Depends(get_db)):
    open_tickets = (
        db.query(Ticket, Vehiculo)
        .join(Vehiculo, Vehiculo.id == Ticket.vehiculo_id)
        .filter(Ticket.estado == "abierto")
        .order_by(Ticket.hora_entrada.desc())
        .all()
    )
    recent_events = db.query(ParkingEvent).order_by(ParkingEvent.id.desc()).limit(20).all()

    active_sessions = [
        ActiveParkingSession(
            ticket_id=ticket.id,
            vehicle_id=vehicle.id,
            plate=vehicle.placa,
            camera_id=None,
            source=None,
            entered_at=ticket.hora_entrada,
            parking_minutes=calculate_minutes(ticket.hora_entrada),
        )
        for ticket, vehicle in open_tickets
    ]

    return ParkingStateResponse(
        occupancy=len(active_sessions),
        active_sessions=active_sessions,
        recent_events=[
            build_event_payload(
                event=row,
                parking_minutes=None,
            )
            for row in recent_events
        ],
    )


@parking_router.get("/events", response_model=list[ParkingEventItem])
def list_recent_events(db: Session = Depends(get_db)):
    rows = db.query(ParkingEvent).order_by(ParkingEvent.id.desc()).limit(50).all()
    return [build_event_payload(event=row, parking_minutes=None) for row in rows]


@parking_router.get("/events/stream")
def stream_events():
    def event_stream():
        queue = broker.subscribe()
        try:
            yield "retry: 5000\n\n"
            while True:
                try:
                    payload = queue.get(timeout=15)
                    yield f"event: parking_event\ndata: {json.dumps(payload)}\n\n"
                except Empty:
                    yield "event: ping\ndata: {}\n\n"
        finally:
            broker.unsubscribe(queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
