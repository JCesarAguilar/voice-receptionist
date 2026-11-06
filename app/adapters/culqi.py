"""Adaptador de salida: órdenes de pago en Culqi (API v2)."""

from datetime import timedelta

import httpx2

from app.domain.models import Booking
from app.domain.ports import PaymentStatus

CULQI_API = "https://api.culqi.com/v2"
# Estados de una orden en Culqi (verificado en integración: confirm=False -> created)
STATES = {
    "created": PaymentStatus.PENDING,
    "pending": PaymentStatus.PENDING,
    "paid": PaymentStatus.PAID,
}


def to_payment_status(culqi_state: str | None) -> PaymentStatus:
    """Traduce el estado de Culqi al del núcleo. Lo desconocido cuenta como fallido."""
    return STATES.get(culqi_state or "", PaymentStatus.FAILED)


class CulqiError(RuntimeError):
    """Culqi rechazó la petición. El mensaje incluye su respuesta."""


class CulqiPayments:
    """Cumple el puerto PaymentPort usando la API de órdenes de Culqi."""

    def __init__(
        self, secret_key: str, hold_minutes: int, timeout_seconds: float = 15.0
    ) -> None:
        self._http = httpx2.Client(
            base_url=CULQI_API,
            headers={"Authorization": f"Bearer {secret_key}"},
            timeout=timeout_seconds,
        )
        self._hold_minutes = hold_minutes

    def create_order(self, booking: Booking, email: str) -> str:
        first_name, _, last_name = booking.client.name.partition(" ")
        expires = booking.created_at + timedelta(minutes=self._hold_minutes)
        payload = {
            "amount": booking.price_cents,
            "currency_code": "PEN",
            "description": f"Consulta {booking.area} - Estudio Lex Andina",
            "order_number": booking.id.hex,
            "expiration_date": int(expires.timestamp()),
            "client_details": {
                "first_name": first_name,
                "last_name": last_name or first_name,
                "email": email,
                "phone_number": booking.client.whatsapp,
            },
            "confirm": False,
        }
        response = self._http.post("/orders", json=payload)
        self._check(response)
        return response.json()["id"]

    def get_status(self, order_id: str) -> PaymentStatus:
        response = self._http.get(f"/orders/{order_id}")
        self._check(response)
        return to_payment_status(response.json().get("state"))

    @staticmethod
    def _check(response: httpx2.Response) -> None:
        if response.is_error:
            raise CulqiError(f"Culqi respondió {response.status_code}: {response.text}")
