"""Fakes en memoria de los puertos: permiten probar el núcleo sin internet."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from app.domain.models import Booking, BookingStatus
from app.domain.ports import (
    BookingRepository,
    CalendarPort,
    Clock,
    MessagingPort,
    PaymentPort,
    PaymentStatus,
    TimeRange,
)


class FixedClock:
    """Reloj que solo avanza cuando el test lo pide."""

    def __init__(self, now: datetime) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


@dataclass
class FakeEvent:
    start: datetime
    end: datetime
    status: str


class FakeCalendar:
    def __init__(self, busy: list[TimeRange] | None = None) -> None:
        self.busy = list(busy or [])
        self.events: dict[str, FakeEvent] = {}
        self._next_id = 1

    def busy_ranges(self, start: datetime, end: datetime) -> list[TimeRange]:
        ranges = self.busy + [TimeRange(e.start, e.end) for e in self.events.values()]
        return [r for r in ranges if r.start < end and r.end > start]

    def create_hold(self, booking: Booking) -> str:
        event_id = f"evt-{self._next_id}"
        self._next_id += 1
        self.events[event_id] = FakeEvent(booking.start, booking.end, "PENDIENTE")
        return event_id

    def mark_confirmed(self, event_id: str, booking: Booking) -> None:
        self.events[event_id].status = "CONFIRMADA"

    def delete_event(self, event_id: str) -> None:
        self.events.pop(event_id, None)


class FakePayments:
    def __init__(self, approve_charges: bool = True) -> None:
        self.orders: dict[str, PaymentStatus] = {}
        self.charges: list[str] = []
        self.approve_charges = approve_charges

    def create_order(self, booking: Booking, email: str) -> str:
        order_id = f"ord-{len(self.orders) + 1}"
        self.orders[order_id] = PaymentStatus.PENDING
        return order_id

    def get_status(self, order_id: str) -> PaymentStatus:
        return self.orders[order_id]

    def mark_paid(self, order_id: str) -> None:
        """Simula que el cliente pagó (en producción lo avisa Culqi)."""
        self.orders[order_id] = PaymentStatus.PAID

    def charge(self, booking: Booking, token_id: str, email: str) -> bool:
        if self.approve_charges:
            self.charges.append(token_id)
        return self.approve_charges


class FakeMessaging:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_whatsapp(self, to: str, text: str) -> None:
        self.sent.append((to, text))


class InMemoryBookingRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Booking] = {}

    def add(self, booking: Booking) -> None:
        self._items[booking.id] = booking.model_copy(deep=True)

    def get(self, booking_id: UUID) -> Booking | None:
        found = self._items.get(booking_id)
        return found.model_copy(deep=True) if found else None

    def get_by_order_id(self, order_id: str) -> Booking | None:
        for booking in self._items.values():
            if booking.payment_order_id == order_id:
                return booking.model_copy(deep=True)
        return None

    def update(self, booking: Booking) -> None:
        self._items[booking.id] = booking.model_copy(deep=True)

    def pending_created_before(self, cutoff: datetime) -> list[Booking]:
        return [
            b.model_copy(deep=True)
            for b in self._items.values()
            if b.status == BookingStatus.PENDING_PAYMENT and b.created_at < cutoff
        ]


# Verificación estática: si un fake no cumple su puerto, Pylance lo marca aquí.
_clock: Clock = FixedClock(datetime(2026, 1, 1))
_calendar: CalendarPort = FakeCalendar()
_payments: PaymentPort = FakePayments()
_messaging: MessagingPort = FakeMessaging()
_repository: BookingRepository = InMemoryBookingRepository()
