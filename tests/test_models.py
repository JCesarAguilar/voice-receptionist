from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from app.domain.models import (
    Area,
    BookingStatus,
    Client,
    InvalidTransitionError,
    format_soles,
    price_for,
)
from tests.factories import LIMA, NOW, make_booking


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
    ["+5112345678", "+1 555 123 4567", "+51 887 654 321"],
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


def test_expired_booking_cannot_be_confirmed():
    booking = make_booking()
    booking.expire()

    with pytest.raises(InvalidTransitionError):
        booking.confirm(booking.created_at)


def test_confirmed_booking_cannot_expire():
    booking = make_booking()
    booking.confirm(booking.created_at)

    with pytest.raises(InvalidTransitionError):
        booking.expire()


def test_late_payment_is_registered_only_once():
    booking = make_booking()
    booking.expire()

    assert booking.register_late_payment(NOW) is True
    assert booking.register_late_payment(NOW) is False


def test_late_payment_requires_expired_booking():
    with pytest.raises(InvalidTransitionError):
        make_booking().register_late_payment(NOW)


def test_whatsapp_without_country_code_is_completed():
    assert Client(name="Ana Torres", whatsapp="987654321").whatsapp == "+51987654321"


def test_whatsapp_error_says_how_many_digits_arrived():
    with pytest.raises(ValidationError, match="Recibí 10 dígitos"):
        Client(name="Ana Torres", whatsapp="+519565822267")
