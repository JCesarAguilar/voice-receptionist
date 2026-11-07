from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

import pytest

from app.domain.models import Area, Booking, BookingStatus, Modality
from app.domain.ports import PaymentPort, PaymentStatus, TimeRange
from app.services.availability import AvailabilityService
from app.services.booking import (
    BookingNotPayableError,
    BookingService,
    SlotUnavailableError,
)
from app.services.handoff import HandoffService
from tests.factories import NOW, RULES, THURSDAY, at, make_client
from tests.fakes import (
    FakeCalendar,
    FakeEvent,
    FakeMessaging,
    FakePayments,
    FixedClock,
    InMemoryBookingRepository,
)

STAFF = "+51900000000"
EMAIL = "ana@example.com"


@dataclass
class Env:
    """El servicio y todos sus fakes, para revisar qué pasó en cada uno."""

    service: BookingService
    availability: AvailabilityService
    calendar: FakeCalendar
    payments: FakePayments
    messaging: FakeMessaging
    repository: InMemoryBookingRepository
    clock: FixedClock


def make_env(busy=None, payments: PaymentPort | None = None) -> Env:
    calendar = FakeCalendar(busy)
    fake_payments = FakePayments()
    messaging = FakeMessaging()
    repository = InMemoryBookingRepository()
    clock = FixedClock(NOW)
    availability = AvailabilityService(calendar, clock, RULES)
    service = BookingService(
        repository=repository,
        calendar=calendar,
        payments=payments or fake_payments,
        messaging=messaging,
        clock=clock,
        availability=availability,
        handoff=HandoffService(messaging, STAFF),
        rules=RULES,
        hold_minutes=30,
        public_base_url="https://demo.test",
        office_address="Av. Larco 123, Miraflores",
    )
    return Env(
        service, availability, calendar, fake_payments, messaging, repository, clock
    )


def book(env: Env, hour: int = 10, **overrides) -> Booking:
    """Paso 1 del flujo: la llamada reserva el horario."""
    data = {
        "client": make_client(),
        "area": Area.LABORAL,
        "modality": Modality.VIRTUAL,
        "start": at(THURSDAY, hour),
        "summary": "Despido sin aviso",
    }
    data.update(overrides)
    return env.service.create(**data)


def open_payment_page(env: Env, booking: Booking) -> str:
    """Paso 2 del flujo: el cliente abre el link y escribe su email."""
    return env.service.start_payment(booking.id, EMAIL)


def stored(env: Env, booking: Booking) -> Booking:
    """La reserva tal como quedó guardada, no el objeto en memoria."""
    found = env.repository.get(booking.id)
    assert found is not None
    return found


def event(env: Env, booking: Booking) -> FakeEvent:
    assert booking.calendar_event_id is not None
    return env.calendar.events[booking.calendar_event_id]


# --- Reservar (durante la llamada) ---


def test_e1_create_holds_slot_and_sends_payment_link():
    env = make_env()

    booking = book(env)

    assert stored(env, booking).status == BookingStatus.PENDING_PAYMENT
    assert booking.price_cents == 12000
    assert event(env, booking).status == "PENDIENTE"
    assert env.payments.orders == {}  # la orden todavía no existe
    to, text = env.messaging.sent[0]
    assert to == "+51987654321"
    assert f"https://demo.test/pagar/{booking.id}" in text
    assert "S/ 120.00" in text


def test_create_rejects_busy_slot():
    env = make_env(busy=[TimeRange(at(THURSDAY, 10), at(THURSDAY, 10, 45))])

    with pytest.raises(SlotUnavailableError):
        book(env)

    assert env.calendar.events == {}
    assert env.messaging.sent == []


def test_slot_taken_between_query_and_booking_is_rejected():
    env = make_env()
    book(env)

    with pytest.raises(SlotUnavailableError):
        book(env, client=make_client(name="Luis Rojas", whatsapp="+51911222333"))


# --- Empezar el pago (en la página) ---


def test_payment_page_creates_the_order():
    env = make_env()
    booking = book(env)

    order_id = open_payment_page(env, booking)

    assert order_id in env.payments.orders
    assert stored(env, booking).payment_order_id == order_id


def test_reloading_the_payment_page_reuses_the_same_order():
    env = make_env()
    booking = book(env)

    first = open_payment_page(env, booking)
    second = open_payment_page(env, booking)

    assert first == second
    assert len(env.payments.orders) == 1


def test_payment_page_rejects_unknown_booking():
    env = make_env()

    with pytest.raises(BookingNotPayableError):
        env.service.start_payment(uuid4(), EMAIL)


def test_payment_page_rejects_expired_booking():
    env = make_env()
    booking = book(env)
    env.clock.advance(timedelta(minutes=31))
    env.service.expire_overdue()

    with pytest.raises(BookingNotPayableError):
        open_payment_page(env, booking)


class FailingPayments(FakePayments):
    """Simula a Culqi caído al crear la orden."""

    def create_order(self, booking: Booking, email: str) -> str:
        raise ConnectionError("Culqi no responde")


def test_culqi_down_keeps_the_booking_pending():
    env = make_env(payments=FailingPayments())
    booking = book(env)

    with pytest.raises(ConnectionError):
        open_payment_page(env, booking)

    assert stored(env, booking).status == BookingStatus.PENDING_PAYMENT
    assert stored(env, booking).payment_order_id is None


# --- Confirmar el pago (aviso de Culqi) ---


def test_e11_payment_confirms_and_notifies():
    env = make_env()
    booking = book(env)
    order_id = open_payment_page(env, booking)
    env.payments.mark_paid(order_id)

    env.service.confirm_payment(order_id)

    assert stored(env, booking).status == BookingStatus.CONFIRMED
    assert event(env, booking).status == "CONFIRMADA"
    assert "confirmada" in env.messaging.sent[-1][1]


def test_repeated_payment_notice_sends_one_confirmation():
    env = make_env()
    booking = book(env)
    order_id = open_payment_page(env, booking)
    env.payments.mark_paid(order_id)

    env.service.confirm_payment(order_id)
    env.service.confirm_payment(order_id)

    assert len(env.messaging.sent) == 2  # link de pago + una confirmación


def test_notice_without_real_payment_does_not_confirm():
    env = make_env()
    booking = book(env)
    order_id = open_payment_page(env, booking)

    env.service.confirm_payment(order_id)

    assert stored(env, booking).status == BookingStatus.PENDING_PAYMENT


def test_failed_payment_status_does_not_confirm():
    env = make_env()
    booking = book(env)
    order_id = open_payment_page(env, booking)
    env.payments.orders[order_id] = PaymentStatus.FAILED

    env.service.confirm_payment(order_id)

    assert stored(env, booking).status == BookingStatus.PENDING_PAYMENT


def test_unknown_order_returns_none():
    assert make_env().service.confirm_payment("ord-no-existe") is None


# --- Vencimiento y pago tardío ---


def test_e10_expires_after_30_minutes_and_frees_the_slot():
    env = make_env()
    booking = book(env)  # nunca abre el link: no hay orden

    env.clock.advance(timedelta(minutes=29))
    assert env.service.expire_overdue() == 0

    env.clock.advance(timedelta(minutes=2))
    assert env.service.expire_overdue() == 1

    assert stored(env, booking).status == BookingStatus.EXPIRED
    assert booking.calendar_event_id not in env.calendar.events
    assert env.availability.is_available(at(THURSDAY, 10))
    assert "venció" in env.messaging.sent[-1][1]


def test_paid_but_lost_notice_is_confirmed_instead_of_expired():
    env = make_env()
    booking = book(env)
    env.payments.mark_paid(open_payment_page(env, booking))

    env.clock.advance(timedelta(minutes=31))
    env.service.expire_overdue()

    assert stored(env, booking).status == BookingStatus.CONFIRMED


def test_e14_late_payment_notifies_staff_and_client_once():
    env = make_env()
    booking = book(env)
    order_id = open_payment_page(env, booking)
    env.clock.advance(timedelta(minutes=31))
    env.service.expire_overdue()
    env.payments.mark_paid(order_id)

    env.service.confirm_payment(order_id)
    env.service.confirm_payment(order_id)  # Culqi avisa otra vez

    assert stored(env, booking).status == BookingStatus.EXPIRED
    staff_texts = [text for to, text in env.messaging.sent if to == STAFF]
    assert len(staff_texts) == 1
    assert "pago tardío" in staff_texts[0]
    assert "recibimos tu pago" in env.messaging.sent[-1][1]


# --- Pagar con token (tarjeta o Yape) ---


def test_token_payment_confirms_the_booking():
    env = make_env()
    booking = book(env)

    paid = env.service.pay_with_token(booking.id, "tkn_test_1", EMAIL)

    assert paid is True
    assert stored(env, booking).status == BookingStatus.CONFIRMED
    assert env.payments.charges == ["tkn_test_1"]
    assert "confirmada" in env.messaging.sent[-1][1]


def test_rejected_card_keeps_the_booking_pending():
    env = make_env(payments=FakePayments(approve_charges=False))
    booking = book(env)

    paid = env.service.pay_with_token(booking.id, "tkn_test_1", EMAIL)

    assert paid is False
    assert stored(env, booking).status == BookingStatus.PENDING_PAYMENT


def test_paid_booking_cannot_be_charged_twice():
    env = make_env()
    booking = book(env)
    env.service.pay_with_token(booking.id, "tkn_test_1", EMAIL)

    with pytest.raises(BookingNotPayableError):
        env.service.pay_with_token(booking.id, "tkn_test_2", EMAIL)

    assert env.payments.charges == ["tkn_test_1"]
