"""Raíz de composición: el único lugar que une el núcleo con los adaptadores reales."""

from dataclasses import dataclass
from functools import lru_cache

from app.adapters.clock import SystemClock
from app.adapters.culqi import CulqiPayments
from app.adapters.google_calendar import GoogleCalendar
from app.adapters.sql_repository import SqlBookingRepository, make_engine
from app.adapters.twilio_whatsapp import TwilioWhatsApp
from app.api.tool_dispatcher import ToolDispatcher
from app.config import get_schedule_rules, get_settings
from app.services.availability import AvailabilityService
from app.services.booking import BookingService
from app.services.handoff import HandoffService


@dataclass(frozen=True)
class Container:
    """Los servicios ya armados, listos para que los use la API."""

    availability: AvailabilityService
    booking: BookingService
    handoff: HandoffService
    dispatcher: ToolDispatcher


@lru_cache
def get_container() -> Container:
    """Arma la app una sola vez, en la primera petición."""
    settings = get_settings()
    rules = get_schedule_rules()
    clock = SystemClock(rules.timezone)

    engine = make_engine(settings.database_url)
    repository = SqlBookingRepository(engine, rules.timezone)
    calendar = GoogleCalendar(
        settings.google_calendar_id,
        settings.google_service_account_file,
        rules.timezone,
    )
    messaging = TwilioWhatsApp(
        settings.twilio_account_sid,
        settings.twilio_auth_token.get_secret_value(),
        settings.twilio_whatsapp_from,
    )
    payments = CulqiPayments(
        settings.culqi_secret_key.get_secret_value(),
        settings.payment_hold_minutes,
    )

    availability = AvailabilityService(
        calendar, clock, rules, settings.max_slot_options
    )
    handoff = HandoffService(messaging, settings.handoff_whatsapp_to)
    booking = BookingService(
        repository=repository,
        calendar=calendar,
        payments=payments,
        messaging=messaging,
        clock=clock,
        availability=availability,
        handoff=handoff,
        rules=rules,
        hold_minutes=settings.payment_hold_minutes,
        public_base_url=settings.public_base_url,
        office_address=settings.office_address,
    )
    dispatcher = ToolDispatcher(availability, booking, handoff, rules.timezone)
    return Container(availability, booking, handoff, dispatcher)


def get_tool_dispatcher() -> ToolDispatcher:
    """Dependencia de FastAPI para el endpoint /vapi/tools."""
    return get_container().dispatcher
