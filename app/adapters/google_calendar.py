"""Adaptador de salida: el calendario del estudio en Google Calendar."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.domain.models import Booking
from app.domain.ports import TimeRange

SCOPES = ["https://www.googleapis.com/auth/calendar"]
PENDING_COLOR = "5"  # amarillo en Google Calendar
CONFIRMED_COLOR = "10"  # verde en Google Calendar


class GoogleCalendar:
    """Cumple el puerto CalendarPort usando la API de Google Calendar."""

    def __init__(
        self, calendar_id: str, credentials_file: str, timezone: ZoneInfo
    ) -> None:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=SCOPES
        )
        self._service = build(
            "calendar", "v3", credentials=credentials, cache_discovery=False
        )
        self._calendar_id = calendar_id
        self._timezone = timezone

    def busy_ranges(self, start: datetime, end: datetime) -> list[TimeRange]:
        body = {
            "timeMin": start.isoformat(),
            "timeMax": end.isoformat(),
            "items": [{"id": self._calendar_id}],
        }
        result = self._service.freebusy().query(body=body).execute()
        busy = result["calendars"][self._calendar_id].get("busy", [])
        return [
            TimeRange(self._parse(item["start"]), self._parse(item["end"]))
            for item in busy
        ]

    def create_hold(self, booking: Booking) -> str:
        body = self._event_body(booking, "PENDIENTE", PENDING_COLOR)
        request = self._service.events().insert(calendarId=self._calendar_id, body=body)
        return request.execute()["id"]

    def mark_confirmed(self, event_id: str, booking: Booking) -> None:
        body = self._event_body(booking, "CONFIRMADA", CONFIRMED_COLOR)
        self._service.events().patch(
            calendarId=self._calendar_id, eventId=event_id, body=body
        ).execute()

    def delete_event(self, event_id: str) -> None:
        try:
            self._service.events().delete(
                calendarId=self._calendar_id, eventId=event_id
            ).execute()
        except HttpError as error:
            if error.resp.status in (404, 410):
                return  # ya no existe: es justo lo que queríamos
            raise

    def _event_body(self, booking: Booking, label: str, color: str) -> dict[str, Any]:
        zone = str(self._timezone)
        return {
            "summary": f"{label} — {booking.client.name} · {booking.area}",
            "description": (
                f"Modalidad: {booking.modality}\n"
                f"WhatsApp: {booking.client.whatsapp}\n"
                f"Resumen: {booking.summary}\n"
                f"Reserva: {booking.id}"
            ),
            "start": {"dateTime": booking.start.isoformat(), "timeZone": zone},
            "end": {"dateTime": booking.end.isoformat(), "timeZone": zone},
            "colorId": color,
        }

    def _parse(self, value: str) -> datetime:
        """Google responde en UTC ('...Z'); lo pasamos a la hora del estudio."""
        return datetime.fromisoformat(value).astimezone(self._timezone)
