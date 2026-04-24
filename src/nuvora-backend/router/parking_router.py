import json
from datetime import datetime, timezone
from queue import Empty, Full, Queue
from threading import Lock

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config.auth import get_current_user, verify_service_api_key
from config.db import SessionLocal
from model.parking_events import ParkingEvent
from model.plate_detections import PlateDetection
from model.tickets import Ticket
from model.turnos import Turno
from model.users import User
from model.vehiculos import Vehiculo
from schema.parking_schema import (
    ActiveParkingSession,
    ParkingDetectionCreate,
    ParkingDetectionResponse,
    ParkingEventItem,
    ParkingManualOperationCreate,
    ParkingManualResponse,
    ParkingOperationResponse,
    ParkingStateResponse,
)
from services.plate_resolution import resolve_plate
from services.tariff_service import calculate_tariff_charge


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


def get_latest_open_turno_id(db: Session) -> int | None:
    turno = (
        db.query(Turno)
        .filter(Turno.estado == "abierto")
        .order_by(Turno.fecha_inicio.desc(), Turno.id.desc())
        .first()
    )
    return turno.id if turno else None


def build_ticket_code(ticket_id: int, detected_at: datetime) -> str:
    return f"TKT-{detected_at.strftime('%Y%m%d')}-{ticket_id:06d}"


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


def resolve_operation_plate(
    db: Session,
    plate: str,
    direction: str,
    allow_context_matching: bool,
):
    initial_resolution = resolve_plate(plate)
    raw_plate = initial_resolution.raw_plate or plate.strip().upper()

    if not allow_context_matching:
        return raw_plate, initial_resolution

    preferred_plates = get_preferred_known_plates(
        db,
        tuple(candidate.plate for candidate in initial_resolution.candidates),
    )
    has_exact_candidate = any(candidate.corrections == 0 for candidate in initial_resolution.candidates)
    context_plates = preferred_plates if direction == "exit" or not has_exact_candidate else []
    return raw_plate, resolve_plate(plate, context_plates)


def finalize_operation(
    db: Session,
    event: ParkingEvent,
    ticket: Ticket | None,
    vehicle: Vehiculo | None,
    parking_minutes: int | None,
    detection_id: int | None,
) -> ParkingOperationResponse:
    db.commit()
    db.refresh(event)
    if ticket:
        db.refresh(ticket)

    open_sessions = db.query(Ticket).filter(Ticket.estado == "abierto").count()
    event_payload = build_event_payload(event, parking_minutes=parking_minutes)
    broker.publish(
        {
            "type": "parking_event",
            "event": event_payload.model_dump(mode="json"),
            "open_sessions": open_sessions,
        }
    )

    return ParkingOperationResponse(
        detection_id=detection_id,
        event_id=event.id,
        ticket_id=ticket.id if ticket else None,
        vehicle_id=vehicle.id if vehicle else None,
        plate=event.plate,
        direction=event.direction,
        status=event.status,
        message=event.message,
        camera_id=event.camera_id,
        source=event.source,
        detected_at=event.detected_at,
        open_sessions=open_sessions,
        parking_minutes=parking_minutes,
    )


def process_parking_operation(
    db: Session,
    *,
    plate: str,
    direction: str,
    detected_at: datetime,
    camera_id: str | None,
    source: str,
    detection: PlateDetection | None = None,
    allow_context_matching: bool,
) -> ParkingOperationResponse:
    raw_plate, resolution = resolve_operation_plate(
        db=db,
        plate=plate,
        direction=direction,
        allow_context_matching=allow_context_matching,
    )

    if resolution.resolved_plate is None:
        ignored_event = ParkingEvent(
            vehiculo_id=None,
            ticket_id=None,
            detection_id=detection.id if detection else None,
            plate=raw_plate,
            direction=direction,
            status="ignored",
            message=resolution.reason or "La deteccion fue descartada.",
            camera_id=camera_id,
            source=source,
            detected_at=detected_at,
        )
        db.add(ignored_event)
        return finalize_operation(
            db=db,
            event=ignored_event,
            ticket=None,
            vehicle=None,
            parking_minutes=None,
            detection_id=detection.id if detection else None,
        )

    normalized_plate = resolution.resolved_plate
    vehicle = db.query(Vehiculo).filter(Vehiculo.placa == normalized_plate).first()
    if vehicle is None:
        vehicle = Vehiculo(placa=normalized_plate)
        db.add(vehicle)
        db.flush()

    ticket = get_open_ticket(db, vehicle.id)
    parking_minutes: int | None = None
    turno_abierto_id = get_latest_open_turno_id(db)

    if direction == "entry":
        if ticket:
            status = "ignored"
            message = "La placa ya tiene una entrada activa."
            parking_minutes = calculate_minutes(ticket.hora_entrada, detected_at)
        else:
            ticket = Ticket(
                codigo_ticket=None,
                vehiculo_id=vehicle.id,
                placa_snapshot=normalized_plate,
                turno_id=turno_abierto_id,
                hora_entrada=detected_at,
                estado="abierto",
            )
            db.add(ticket)
            db.flush()

            processed_event = ParkingEvent(
                vehiculo_id=vehicle.id,
                ticket_id=ticket.id,
                detection_id=detection.id if detection else None,
                plate=normalized_plate,
                direction=direction,
                status="processed",
                message="Entrada registrada correctamente.",
                camera_id=camera_id,
                source=source,
                detected_at=detected_at,
            )
            db.add(processed_event)
            db.flush()

            ticket.codigo_ticket = build_ticket_code(ticket.id, detected_at)
            ticket.entry_event_id = processed_event.id
            return finalize_operation(
                db=db,
                event=processed_event,
                ticket=ticket,
                vehicle=vehicle,
                parking_minutes=None,
                detection_id=detection.id if detection else None,
            )
    else:
        if ticket is None:
            status = "ignored"
            message = "No existe una entrada activa para esta placa."
        else:
            parking_minutes = calculate_minutes(ticket.hora_entrada, detected_at)
            tariff_calculation = calculate_tariff_charge(db, detected_at, parking_minutes)
            processed_event = ParkingEvent(
                vehiculo_id=vehicle.id,
                ticket_id=ticket.id,
                detection_id=detection.id if detection else None,
                plate=normalized_plate,
                direction=direction,
                status="processed",
                message="Salida registrada correctamente.",
                camera_id=camera_id,
                source=source,
                detected_at=detected_at,
            )
            db.add(processed_event)
            db.flush()

            ticket.hora_salida = detected_at
            ticket.estado = "cerrado"
            ticket.tarifa_id = tariff_calculation.tarifa.id if tariff_calculation.tarifa else None
            ticket.minutos_cobrados = tariff_calculation.minutos_cobrados
            ticket.monto_total = tariff_calculation.monto_total
            ticket.turno_cierre_id = turno_abierto_id
            ticket.exit_event_id = processed_event.id
            if tariff_calculation.tarifa:
                processed_event.message = (
                    f"Salida registrada correctamente. "
                    f"Tarifa {tariff_calculation.tarifa.tipo} aplicada por {ticket.monto_total}."
                )
            else:
                processed_event.message = "Salida registrada correctamente. No habia una tarifa activa configurada."
            return finalize_operation(
                db=db,
                event=processed_event,
                ticket=ticket,
                vehicle=vehicle,
                parking_minutes=parking_minutes,
                detection_id=detection.id if detection else None,
            )

    if resolution.corrections:
        message = f"Se asume la placa {normalized_plate}. {message}"

    ignored_event = ParkingEvent(
        vehiculo_id=vehicle.id,
        ticket_id=ticket.id if ticket else None,
        detection_id=detection.id if detection else None,
        plate=normalized_plate,
        direction=direction,
        status=status,
        message=message,
        camera_id=camera_id,
        source=source,
        detected_at=detected_at,
    )
    db.add(ignored_event)
    return finalize_operation(
        db=db,
        event=ignored_event,
        ticket=ticket,
        vehicle=vehicle,
        parking_minutes=parking_minutes,
        detection_id=detection.id if detection else None,
    )


@parking_router.post("/detections", response_model=ParkingDetectionResponse, dependencies=[Depends(verify_service_api_key)])
def process_detection(data: ParkingDetectionCreate, db: Session = Depends(get_db)):
    detected_at = normalize_detected_at(data.detected_at)
    bbox = data.bounding_box

    detection = PlateDetection(
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
        source=data.source or f"vehicle-{data.direction}-service",
        detected_at=detected_at,
    )
    db.add(detection)
    db.flush()

    result = process_parking_operation(
        db=db,
        plate=data.plate,
        direction=data.direction,
        detected_at=detected_at,
        camera_id=data.camera_id,
        source=data.source or f"vehicle-{data.direction}-service",
        detection=detection,
        allow_context_matching=True,
    )

    return ParkingDetectionResponse(
        detection_id=detection.id,
        event_id=result.event_id,
        ticket_id=result.ticket_id,
        vehicle_id=result.vehicle_id,
        plate=result.plate,
        direction=result.direction,
        status=result.status,
        message=result.message,
        camera_id=result.camera_id,
        source=result.source,
        detected_at=result.detected_at,
        open_sessions=result.open_sessions,
        parking_minutes=result.parking_minutes,
    )


@parking_router.post("/manual/entry", response_model=ParkingManualResponse)
def register_manual_entry(
    data: ParkingManualOperationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    detected_at = normalize_detected_at(data.detected_at)
    return process_parking_operation(
        db=db,
        plate=data.plate,
        direction="entry",
        detected_at=detected_at,
        camera_id=data.camera_id,
        source=f"manual:{current_user.usuario}",
        allow_context_matching=False,
    )


@parking_router.post("/manual/exit", response_model=ParkingManualResponse)
def register_manual_exit(
    data: ParkingManualOperationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    detected_at = normalize_detected_at(data.detected_at)
    return process_parking_operation(
        db=db,
        plate=data.plate,
        direction="exit",
        detected_at=detected_at,
        camera_id=data.camera_id,
        source=f"manual:{current_user.usuario}",
        allow_context_matching=False,
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
