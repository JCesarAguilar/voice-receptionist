"""Caso de uso: reservar, confirmar con el pago y vencer reservas sin pagar."""

from datetime import datetime, timedelta

from app.domain.models import (
    Area,
    Booking,
    BookingStatus,
    Client,
    HandoffReason,
    Modality,
    format_soles,
    price_for,
)
from app.domain.ports import (
    BookingRepository,
    CalendarPort,
    Clock,
    MessagingPort,
    PaymentPort,
    PaymentStatus,
)
from app.domain.rules import ScheduleRules, slot_end
from app.services import messages
from app.services.availability import AvailabilityService
from app.services.handoff import HandoffService


class SlotUnavailableError(ValueError):
    """El horario ya no está libre o no cumple las reglas."""


class BookingService:
    def __init__(
        self,
        *,
        repository: BookingRepository,
        calendar: CalendarPort,
        payments: PaymentPort,
        messaging: MessagingPort,
        clock: Clock,
        availability: AvailabilityService,
        handoff: HandoffService,
        rules: ScheduleRules,
        hold_minutes: int,
        public_base_url: str,
        office_address: str,
    ) -> None:
        self._repository = repository
        self._calendar = calendar
        self._payments = payments
        self._messaging = messaging
        self._clock = clock
        self._availability = availability
        self._handoff = handoff
        self._rules = rules
        self._hold_minutes = hold_minutes
        self._public_base_url = public_base_url.rstrip("/")
        self._office_address = office_address

    def create(
        self,
        *,
        client: Client,
        area: Area,
        modality: Modality,
        start: datetime,
        summary: str,
    ) -> Booking:
        """Retiene el horario, crea la orden de pago y envía el link por WhatsApp."""
        start = start.astimezone(self._rules.timezone)
        if not self._availability.is_available(start):
            raise SlotUnavailableError("Ese horario ya no está disponible.")

        booking = Booking(
            client=client,
            area=area,
            modality=modality,
            start=start,
            end=slot_end(start, self._rules),
            summary=summary,
            price_cents=price_for(area),
            created_at=self._clock.now(),
        )
        booking.calendar_event_id = self._calendar.create_hold(booking)
        try:
            booking.payment_order_id = self._payments.create_order(booking)
        except Exception:
            # Sin orden de pago no hay reserva: liberamos el horario retenido.
            self._calendar.delete_event(booking.calendar_event_id)
            raise

        self._repository.add(booking)
        link = f"{self._public_base_url}/pagar/{booking.id}"
        text = messages.payment_link_message(booking, link, self._hold_minutes)
        self._messaging.send_whatsapp(booking.client.whatsapp, text)
        return booking

    def confirm_payment(self, order_id: str) -> Booking | None:
        """Lo llama el webhook de Culqi. Repetir el aviso no hace nada."""
        booking = self._repository.get_by_order_id(order_id)
        if booking is None:
            return None
        if booking.status == BookingStatus.CONFIRMED:
            return booking  # ya confirmada: idempotencia
        if not self._is_paid(order_id):
            return booking  # no confiamos en el aviso: preguntamos a Culqi
        if booking.status == BookingStatus.EXPIRED:
            self._handle_late_payment(booking)
            return booking
        self._confirm(booking)
        return booking

    def expire_overdue(self) -> int:
        """Vence las reservas sin pagar. Devuelve cuántas venció."""
        cutoff = self._clock.now() - timedelta(minutes=self._hold_minutes)
        expired = 0
        for booking in self._repository.pending_created_before(cutoff):
            if booking.payment_order_id and self._is_paid(booking.payment_order_id):
                self._confirm(booking)  # pagó, pero el aviso de Culqi no llegó
                continue
            booking.expire()
            if booking.calendar_event_id:
                self._calendar.delete_event(booking.calendar_event_id)
            self._repository.update(booking)
            text = messages.expired_message(booking)
            self._messaging.send_whatsapp(booking.client.whatsapp, text)
            expired += 1
        return expired

    def _is_paid(self, order_id: str) -> bool:
        return self._payments.get_status(order_id) == PaymentStatus.PAID

    def _confirm(self, booking: Booking) -> None:
        booking.confirm(self._clock.now())
        if booking.calendar_event_id:
            self._calendar.mark_confirmed(booking.calendar_event_id, booking)
        self._repository.update(booking)
        text = messages.confirmation_message(booking, self._office_address)
        self._messaging.send_whatsapp(booking.client.whatsapp, text)

    def _handle_late_payment(self, booking: Booking) -> None:
        """Pagó después de vencer: el horario no vuelve, avisamos a una persona."""
        if not booking.register_late_payment(self._clock.now()):
            return  # ya avisado antes
        self._repository.update(booking)
        when = messages.format_when(booking.start)
        price = format_soles(booking.price_cents)
        self._handoff.notify(
            reason=HandoffReason.LATE_PAYMENT,
            client=booking.client,
            area=booking.area,
            summary=f"Pagó {price} tarde; su reserva del {when} había vencido.",
        )
        text = messages.late_payment_message(booking)
        self._messaging.send_whatsapp(booking.client.whatsapp, text)
