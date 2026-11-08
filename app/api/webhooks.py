"""Adaptador de entrada: los avisos que Culqi envía cuando cambia una orden."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.vapi_tools import verify_vapi_secret
from app.container import get_booking_service, get_call_log_service
from app.schemas.webhooks import CulqiEvent, VapiServerRequest
from app.services.booking import BookingService
from app.services.calls import CallLogService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

ORDER_CHANGED = "order.status.changed"
END_OF_CALL = "end-of-call-report"


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


@router.post("/vapi", dependencies=[Depends(verify_vapi_secret)])
def vapi_webhook(
    request: VapiServerRequest,
    service: Annotated[CallLogService, Depends(get_call_log_service)],
) -> dict[str, str]:
    """Al terminar cada llamada, Vapi manda el reporte: se guarda y se traza."""
    message = request.message
    if message.type != END_OF_CALL or message.call is None:
        return {"status": "ignored"}
    service.record(
        call_id=message.call.id,
        ended_reason=message.ended_reason,
        duration_seconds=message.duration_seconds or 0.0,
        cost_usd=message.cost or 0.0,
        transcript=message.full_transcript(),
        summary=message.call_summary(),
    )
    return {"status": "saved"}
