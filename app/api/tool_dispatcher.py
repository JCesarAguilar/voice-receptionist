"""Traduce cada tool call de Vapi en una llamada a los servicios del núcleo."""

import logging
from collections.abc import Callable
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from app.domain.models import Client, format_soles
from app.domain.rules import ScheduleRuleError
from app.schemas.tools import (
    CheckAvailabilityArgs,
    CreateBookingArgs,
    HandoffArgs,
    ToolCall,
    ToolResult,
)
from app.services.availability import AvailabilityService
from app.services.booking import BookingService, SlotUnavailableError
from app.services.handoff import HandoffService
from app.services.messages import format_when

logger = logging.getLogger(__name__)

ToolHandler = Callable[[dict[str, Any]], str]


def readable(error: ValidationError) -> str:
    """Convierte los errores de Pydantic en un texto que el agente entienda."""
    parts = []
    for item in error.errors():
        field = ".".join(str(part) for part in item["loc"]) or "datos"
        parts.append(f"{field}: {item['msg']}")
    return "Datos inválidos. " + "; ".join(parts)


class ToolDispatcher:
    """Elige el handler de cada tool. Agregar una tool = registrar un handler."""

    def __init__(
        self,
        availability: AvailabilityService,
        booking: BookingService,
        handoff: HandoffService,
        timezone: ZoneInfo,
    ) -> None:
        self._availability = availability
        self._booking = booking
        self._handoff = handoff
        self._timezone = timezone
        self._handlers: dict[str, ToolHandler] = {
            "check_availability": self._check_availability,
            "create_booking": self._create_booking,
            "handoff_to_human": self._handoff_to_human,
        }

    def run(self, call: ToolCall) -> ToolResult:
        handler = self._handlers.get(call.function.name)
        if handler is None:
            message = f"La tool '{call.function.name}' no existe."
            return ToolResult(tool_call_id=call.id, error=message)
        try:
            text = handler(call.function.arguments)
        except ValidationError as error:
            return ToolResult(tool_call_id=call.id, error=readable(error))
        except Exception:
            logger.exception("Falló la tool %s", call.function.name)
            message = "Hubo un problema técnico. Ofrece derivar a una persona."
            return ToolResult(tool_call_id=call.id, error=message)
        return ToolResult(tool_call_id=call.id, result=text)

    def _check_availability(self, raw: dict[str, Any]) -> str:
        args = CheckAvailabilityArgs.model_validate(raw)
        found = self._availability.find_slots(args.date, args.preferred_time)
        if not found.slots:
            return found.message or "No hay horarios libres en los próximos días."
        options = "; ".join(
            f"{format_when(slot)} (start={slot.isoformat()})" for slot in found.slots
        )
        return f"{found.message} Horarios libres: {options}".strip()

    def _create_booking(self, raw: dict[str, Any]) -> str:
        args = CreateBookingArgs.model_validate(raw)
        client = Client(name=args.client_name, whatsapp=args.client_whatsapp)
        start = args.start
        if start.tzinfo is None:
            start = start.replace(tzinfo=self._timezone)  # el LLM la dio en hora local
        try:
            booking = self._booking.create(
                client=client,
                area=args.area,
                modality=args.modality,
                start=start,
                summary=args.summary,
            )
        except (SlotUnavailableError, ScheduleRuleError) as error:
            return f"No se pudo reservar: {error} Vuelve a consultar disponibilidad."
        return (
            f"Reserva separada para el {format_when(booking.start)}, "
            f"precio {format_soles(booking.price_cents)}. Se envió el link de pago "
            "por WhatsApp; la cita se confirma cuando el pago se acredita."
        )

    def _handoff_to_human(self, raw: dict[str, Any]) -> str:
        args = HandoffArgs.model_validate(raw)
        client = Client(name=args.client_name, whatsapp=args.client_whatsapp)
        self._handoff.notify(
            reason=args.reason, client=client, summary=args.summary, area=args.area
        )
        return "Aviso enviado al equipo. Dile al cliente que lo contactarán pronto."
