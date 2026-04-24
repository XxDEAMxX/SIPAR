from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from model.tarifas import Tarifa


@dataclass
class TariffCalculation:
    tarifa: Tarifa | None
    minutos_cobrados: int
    monto_total: Decimal


def time_in_range(target: time, start: time, end: time) -> bool:
    if start == end:
        return True
    if start < end:
        return start <= target < end
    return target >= start or target < end


def get_active_tariff_for_datetime(db: Session, reference: datetime) -> Tarifa | None:
    target = reference.time()
    tarifas = (
        db.query(Tarifa)
        .filter(Tarifa.activa.is_(True))
        .order_by(Tarifa.id.asc())
        .all()
    )
    for tarifa in tarifas:
        if time_in_range(target, tarifa.hora_inicio, tarifa.hora_fin):
            return tarifa
    return None


def calculate_tariff_charge(db: Session, reference: datetime, parking_minutes: int) -> TariffCalculation:
    tarifa = get_active_tariff_for_datetime(db, reference)
    if tarifa is None:
        return TariffCalculation(tarifa=None, minutos_cobrados=0, monto_total=Decimal("0.00"))

    adjusted_minutes = max(0, parking_minutes - int(tarifa.minutos_gracia or 0))
    if adjusted_minutes == 0:
        return TariffCalculation(tarifa=tarifa, minutos_cobrados=0, monto_total=Decimal("0.00"))

    fraction = max(1, int(tarifa.fraccion_minutos or 60))
    billed_units = (adjusted_minutes + fraction - 1) // fraction
    billed_minutes = billed_units * fraction
    amount = (Decimal(str(tarifa.valor_hora)) * Decimal(billed_units)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    return TariffCalculation(
        tarifa=tarifa,
        minutos_cobrados=billed_minutes,
        monto_total=amount,
    )
