"""Textos de WhatsApp que recibe el cliente."""

from datetime import datetime

from app.domain.models import (
    Area,
    Booking,
    Client,
    HandoffReason,
    Modality,
    format_soles,
)

DAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MONTHS = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def format_when(moment: datetime) -> str:
    """Ejemplo: 'jueves 12 de noviembre a las 10:00'."""
    day = DAYS[moment.weekday()]
    month = MONTHS[moment.month - 1]
    return f"{day} {moment.day} de {month} a las {moment:%H:%M}"


def payment_link_message(booking: Booking, link: str, hold_minutes: int) -> str:
    return (
        f"Hola {booking.client.name}, separamos tu consulta de {booking.area} "
        f"el {format_when(booking.start)} ({booking.modality}). "
        f"Para confirmarla, paga {format_soles(booking.price_cents)} "
        f"en los próximos {hold_minutes} minutos: {link}"
    )


def confirmation_message(booking: Booking, office_address: str) -> str:
    if booking.modality == Modality.PRESENCIAL:
        place = f"Te esperamos en {office_address}."
    else:
        place = "Te enviaremos el link de la videollamada antes de la cita."
    return (
        f"¡Listo, {booking.client.name}! Tu consulta de {booking.area} "
        f"está confirmada para el {format_when(booking.start)}. {place}"
    )


def expired_message(booking: Booking) -> str:
    return (
        f"Hola {booking.client.name}, tu reserva del "
        f"{format_when(booking.start)} venció porque no se registró el pago. "
        "Si aún te interesa, vuelve a llamarnos."
    )


def handoff_message(
    reason: HandoffReason, client: Client, summary: str, area: Area | None
) -> str:
    """Mensaje para el responsable del estudio."""
    area_text = area if area else "sin definir"
    return (
        f"Derivación por {reason}. Cliente: {client.name}, {client.whatsapp}. "
        f"Área: {area_text}. Resumen: {summary}"
    )


def late_payment_message(booking: Booking) -> str:
    return (
        f"Hola {booking.client.name}, recibimos tu pago, pero tu reserva del "
        f"{format_when(booking.start)} ya había vencido. "
        "El estudio te contactará para reagendar o devolverte el dinero."
    )
