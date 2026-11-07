"""Adaptador de entrada: lo que llama la página de pago desde el navegador."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.container import get_booking_service
from app.schemas.payments import (
    ChargeRequest,
    ChargeResponse,
    StartPaymentRequest,
    StartPaymentResponse,
)
from app.services.booking import BookingNotPayableError, BookingService

router = APIRouter(prefix="/payments", tags=["payments"])

Service = Annotated[BookingService, Depends(get_booking_service)]


def not_payable(error: BookingNotPayableError) -> HTTPException:
    """409: la reserva existe en la URL, pero ya no acepta pagos."""
    return HTTPException(status.HTTP_409_CONFLICT, detail=str(error))


@router.post("/{booking_id}/order")
def start_payment(
    booking_id: UUID, body: StartPaymentRequest, service: Service
) -> StartPaymentResponse:
    """El cliente escribió su email: se crea (o reutiliza) la orden."""
    try:
        order_id = service.start_payment(booking_id, body.email)
    except BookingNotPayableError as error:
        raise not_payable(error) from error
    return StartPaymentResponse(order_id=order_id)


@router.post("/{booking_id}/charge")
def charge(booking_id: UUID, body: ChargeRequest, service: Service) -> ChargeResponse:
    """Culqi devolvió un token (tarjeta o Yape): se cobra y se confirma."""
    try:
        paid = service.pay_with_token(booking_id, body.token_id, body.email)
    except BookingNotPayableError as error:
        raise not_payable(error) from error
    return ChargeResponse(paid=paid)
