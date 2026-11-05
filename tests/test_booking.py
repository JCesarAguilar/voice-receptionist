from dataclasses import dataclass
from datetime import timedelta

import pytest

from app.domain.models import Area, Booking, BookingStatus, Modality
from app.domain.ports import PaymentPort, PaymentStatus, TimeRange
from app.services.availability import AvailabilityService
from app.services.booking import BookingService, SlotUnavailableError
from tests.factories import NOW, RULES, THURSDAY, at, make_client
from tests.fakes import (
    FakeCalendar,
    FakeEvent,
    FakeMessaging,
    FakePayments,
    FixedClock,
    InMemoryBookingRepository,
)


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
        rules=RULES,
        hold_minutes=30,
        public_base_url="https://demo.test",
        office_address="Av. Larco 123, Miraflores",
    )
    return Env(
        service, availability, calendar, fake_payments, messaging, repository, clock
    )


def book(env: Env, hour: int = 10, **overrides) -> Booking:
    data = {
        "client": make_client(),
        "area": Area.LABORAL,
        "modality": Modality.VIRTUAL,
        "start": at(THURSDAY, hour),
        "summary": "Despido sin aviso",
    }
    data.update(overrides)
    return env.service.create(**data)


def stored(env: Env, booking: Booking) -> Booking:
    """La reserva tal como quedó guardada, no el objeto en memoria."""
    found = env.repository.get(booking.id)
    assert found is not None
    return found


def order_id(booking: Booking) -> str:
    assert booking.payment_order_id is not None
    return booking.payment_order_id


def event(env: Env, booking: Booking) -> FakeEvent:
    assert booking.calendar_event_id is not None
    return env.calendar.events[booking.calendar_event_id]


def test_e1_create_holds_slot_and_sends_payment_link():
    env = make_env()

    booking = book(env)

    assert stored(env, booking).status == BookingStatus.PENDING_PAYMENT
    assert booking.price_cents == 12000
    assert event(env, booking).status == "PENDIENTE"
    assert order_id(booking) in env.payments.orders
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


def test_e11_payment_confirms_and_notifies():
    env = make_env()
    booking = book(env)
    env.payments.mark_paid(order_id(booking))

    env.service.confirm_payment(order_id(booking))

    assert stored(env, booking).status == BookingStatus.CONFIRMED
    assert event(env, booking).status == "CONFIRMADA"
    assert "confirmada" in env.messaging.sent[-1][1]


def test_repeated_payment_notice_sends_one_confirmation():
    env = make_env()
    booking = book(env)
    env.payments.mark_paid(order_id(booking))

    env.service.confirm_payment(order_id(booking))
    env.service.confirm_payment(order_id(booking))

    assert len(env.messaging.sent) == 2  # link de pago + una confirmación


def test_notice_without_real_payment_does_not_confirm():
    env = make_env()
    booking = book(env)

    env.service.confirm_payment(order_id(booking))

    assert stored(env, booking).status == BookingStatus.PENDING_PAYMENT


def test_failed_payment_status_does_not_confirm():
    env = make_env()
    booking = book(env)
    env.payments.orders[order_id(booking)] = PaymentStatus.FAILED

    env.service.confirm_payment(order_id(booking))

    assert stored(env, booking).status == BookingStatus.PENDING_PAYMENT


def test_unknown_order_returns_none():
    assert make_env().service.confirm_payment("ord-no-existe") is None


def test_e10_expires_after_30_minutes_and_frees_the_slot():
    env = make_env()
    booking = book(env)

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
    env.payments.mark_paid(order_id(booking))

    env.clock.advance(timedelta(minutes=31))
    env.service.expire_overdue()

    assert stored(env, booking).status == BookingStatus.CONFIRMED


class FailingPayments(FakePayments):
    """Simula a Culqi caído al crear la orden."""

    def create_order(self, booking: Booking) -> str:
        raise ConnectionError("Culqi no responde")


def test_failed_payment_order_releases_the_held_slot():
    env = make_env(payments=FailingPayments())

    with pytest.raises(ConnectionError):
        book(env)

    assert env.calendar.events == {}
    assert env.availability.is_available(at(THURSDAY, 10))
