"""Prueba manual del adaptador de Google Calendar (T10).

Uso: python -m scripts.try_calendar
"""

from datetime import datetime, timedelta

from app.adapters.google_calendar import GoogleCalendar
from app.config import get_schedule_rules, get_settings
from app.domain.models import Area, Booking, Client, Modality, price_for
from app.domain.ports import TimeRange
from app.domain.rules import slot_end


def show(ranges: list[TimeRange]) -> str:
    if not ranges:
        return "libre"
    return ", ".join(f"{r.start:%H:%M}-{r.end:%H:%M}" for r in ranges)


def main() -> None:
    settings = get_settings()
    rules = get_schedule_rules()
    calendar = GoogleCalendar(
        settings.google_calendar_id,
        settings.google_service_account_file,
        rules.timezone,
    )

    now = datetime.now(rules.timezone)
    tomorrow = now + timedelta(days=1)
    start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
    booking = Booking(
        client=Client(name="Prueba T10", whatsapp="+51999999999"),
        area=Area.LABORAL,
        modality=Modality.VIRTUAL,
        start=start,
        end=slot_end(start, rules),
        summary="Evento de prueba del adaptador",
        price_cents=price_for(Area.LABORAL),
        created_at=now,
    )

    print(f"Turno de prueba: {start:%d/%m %H:%M}")
    print(f"1. Antes de crear: {show(calendar.busy_ranges(start, booking.end))}")

    event_id = calendar.create_hold(booking)
    print(f"2. Evento PENDIENTE creado (id {event_id})")
    print(f"   Ahora el turno está: {show(calendar.busy_ranges(start, booking.end))}")
    input("   Míralo en tu calendario (amarillo) y presiona Enter... ")

    calendar.mark_confirmed(event_id, booking)
    input("3. Pasó a CONFIRMADA (verde). Míralo y presiona Enter para borrarlo... ")

    calendar.delete_event(event_id)
    print(f"4. Borrado. El turno está: {show(calendar.busy_ranges(start, booking.end))}")

    calendar.delete_event(event_id)
    print("5. Borrarlo otra vez no falla (idempotencia). ¡Listo!")


if __name__ == "__main__":
    main()