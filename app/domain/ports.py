"""Puertos: lo que el núcleo necesita del exterior, sin saber quién lo hace."""

from datetime import datetime
from enum import StrEnum
from typing import NamedTuple, Protocol
from uuid import UUID

from app.domain.models import Booking


class TimeRange(NamedTuple):
    """Un bloque de tiempo ocupado en el calendario."""

    start: datetime
    end: datetime


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"


class Clock(Protocol):
    """La hora actual. En los tests se reemplaza por un reloj fijo."""

    def now(self) -> datetime: ...


class CalendarPort(Protocol):
    def busy_ranges(self, start: datetime, end: datetime) -> list[TimeRange]: ...

    def create_hold(self, booking: Booking) -> str:
        """Crea el evento PENDIENTE y devuelve su id."""
        ...

    def mark_confirmed(self, event_id: str, booking: Booking) -> None: ...

    def delete_event(self, event_id: str) -> None: ...


class PaymentPort(Protocol):
    def create_order(self, booking: Booking, email: str) -> str:
        """Crea la orden con el email que escribió el cliente. Devuelve su id."""
        ...

    def get_status(self, order_id: str) -> PaymentStatus: ...


class MessagingPort(Protocol):
    def send_whatsapp(self, to: str, text: str) -> None:
        """`to` es un número en formato +51... El adaptador agrega lo que necesite."""
        ...


class BookingRepository(Protocol):
    def add(self, booking: Booking) -> None: ...

    def get(self, booking_id: UUID) -> Booking | None: ...

    def get_by_order_id(self, order_id: str) -> Booking | None: ...

    def update(self, booking: Booking) -> None: ...

    def pending_created_before(self, cutoff: datetime) -> list[Booking]: ...
