from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.domain.models import (
    Area,
    Booking,
    BookingStatus,
    Client,
    Modality,
    format_soles,
    price_for,
)

LIMA = ZoneInfo("America/Lima")


def make_booking(**overrides) -> Booking:
    start = datetime(2026, 11, 12, 10, 0, tzinfo=LIMA)
    data = {
        "client": Client(name="Ana Torres", whatsapp="+51987654321"),
        "area": Area.LABORAL,
        "modality": Modality.VIRTUAL,
        "start": start,
        "end": start + timedelta(minutes=45),
        "summary": "Despido sin aviso",
        "price_cents": price_for(Area.LABORAL),
        "created_at": datetime(2026, 11, 10, 9, 0, tzinfo=LIMA),
    }
    data.update(overrides)
    return Booking(**data)


@pytest.mark.parametrize(
    ("area", "expected_cents"),
    [
        (Area.CIVIL, 15000),
        (Area.PENAL, 20000),
        (Area.LABORAL, 12000),
        (Area.FAMILIA, 15000),
    ],
)
def test_price_for_each_area(area, expected_cents):
    assert price_for(area) == expected_cents


def test_format_soles():
    assert format_soles(12000) == "S/ 120.00"


def test_whatsapp_is_normalized():
    client = Client(name="  Ana Torres  ", whatsapp="+51 987-654 321")

    assert client.whatsapp == "+51987654321"
    assert client.name == "Ana Torres"


@pytest.mark.parametrize(
    "bad_number",
    ["987654321", "+5112345678", "+1 555 123 4567", "+51 887 654 321"],
)
def test_invalid_whatsapp_is_rejected(bad_number):
    with pytest.raises(ValidationError):
        Client(name="Ana Torres", whatsapp=bad_number)


def test_new_booking_starts_pending_payment():
    booking = make_booking()

    assert booking.status == BookingStatus.PENDING_PAYMENT
    assert booking.calendar_event_id is None


def test_booking_rejects_date_without_timezone():
    with pytest.raises(ValidationError):
        make_booking(start=datetime(2026, 11, 12, 10, 0))


def test_booking_rejects_end_before_start():
    start = datetime(2026, 11, 12, 10, 0, tzinfo=LIMA)

    with pytest.raises(ValidationError):
        make_booking(start=start, end=start - timedelta(minutes=1))


def test_booking_rejects_unknown_area():
    with pytest.raises(ValidationError):
        make_booking(area="tributario")