from app.domain.models import Modality
from app.services.messages import (
    confirmation_message,
    expired_message,
    format_when,
    payment_link_message,
)
from tests.factories import THURSDAY, at, make_booking


def test_format_when_in_spanish():
    assert format_when(at(THURSDAY, 10)) == "jueves 12 de noviembre a las 10:00"


def test_payment_link_has_price_deadline_and_link():
    text = payment_link_message(make_booking(), "https://demo.test/pagar/1", 30)

    assert "Ana Torres" in text
    assert "laboral" in text
    assert "S/ 120.00" in text
    assert "30 minutos" in text
    assert "https://demo.test/pagar/1" in text


def test_confirmation_depends_on_modality():
    address = "Av. Larco 123, Miraflores"
    presencial = make_booking(modality=Modality.PRESENCIAL)
    virtual = make_booking(modality=Modality.VIRTUAL)

    assert address in confirmation_message(presencial, address)
    assert "videollamada" in confirmation_message(virtual, address)


def test_expired_message_explains_why():
    assert "venció" in expired_message(make_booking())
