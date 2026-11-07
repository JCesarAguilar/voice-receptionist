"""Adaptador de entrada: la página HTML que el cliente abre desde WhatsApp."""

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import Settings, get_settings
from app.container import get_booking_service
from app.domain.models import format_soles
from app.services.booking import BookingService
from app.services.messages import format_when

ROOT = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=ROOT / "templates")

router = APIRouter(tags=["pagina de pago"])


@router.get("/pagar/{booking_id}", response_class=HTMLResponse)
def payment_page(
    request: Request,
    booking_id: UUID,
    service: Annotated[BookingService, Depends(get_booking_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> HTMLResponse:
    """Resumen de la cita + checkout de Culqi (o el aviso si ya no se paga)."""
    booking = service.find(booking_id)
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada.")
    context = {
        "booking_id": str(booking.id),
        "status": booking.status.value,
        "area": booking.area.value.capitalize(),
        "modality": booking.modality.value,
        "when": format_when(booking.start),
        "price": format_soles(booking.price_cents),
        "amount_cents": booking.price_cents,
        "public_key": settings.culqi_public_key,
    }
    return templates.TemplateResponse(request, "pagar.html", context)
