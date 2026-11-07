"""Adaptador de entrada: los avisos que Culqi envía cuando cambia una orden."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.container import get_booking_service
from app.schemas.webhooks import CulqiEvent
from app.services.booking import BookingService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

ORDER_CHANGED = "order.status.changed"


@router.post("/culqi")
def culqi_webhook(
    event: CulqiEvent,
    service: Annotated[BookingService, Depends(get_booking_service)],
) -> dict[str, str]:
    """Respondemos 200 rápido; la verdad del pago la consulta el servicio."""
    order_id = event.order_id() if event.type == ORDER_CHANGED else None
    if order_id is None:
        return {"status": "ignored"}
    booking = service.confirm_payment(order_id)
    return {"status": "processed" if booking else "unknown_order"}
