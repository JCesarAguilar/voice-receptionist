"""Datos de prueba compartidos por varios tests."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.domain.models import Area, Booking, Client, Modality, price_for
from app.domain.rules import ScheduleRules

LIMA = ZoneInfo("America/Lima")
RULES = ScheduleRules(
    timezone=LIMA,
    opening_hour=9,
    closing_hour=18,
    consultation_minutes=45,
    buffer_minutes=15,
    min_advance_hours=2,
    max_advance_days=30,
)
NOW = datetime(2026, 11, 10, 9, 0, tzinfo=LIMA)  # martes 9:00
THURSDAY = date(2026, 11, 12)
SATURDAY = date(2026, 11, 14)


def at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=LIMA)


def make_client(**overrides) -> Client:
    data = {"name": "Ana Torres", "whatsapp": "+51987654321"}
    data.update(overrides)
    return Client(**data)


def make_booking(**overrides) -> Booking:
    start = at(THURSDAY, 10)
    data = {
        "client": make_client(),
        "area": Area.LABORAL,
        "modality": Modality.VIRTUAL,
        "start": start,
        "end": start + timedelta(minutes=45),
        "summary": "Despido sin aviso",
        "price_cents": price_for(Area.LABORAL),
        "created_at": NOW,
    }
    data.update(overrides)
    return Booking(**data)
