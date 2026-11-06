"""Adaptador de salida: envía mensajes de WhatsApp con Twilio."""

from twilio.rest import Client as TwilioClient


class TwilioWhatsApp:
    """Cumple el puerto MessagingPort usando la API de Twilio."""

    def __init__(self, account_sid: str, auth_token: str, from_number: str) -> None:
        self._client = TwilioClient(account_sid, auth_token)
        self._from = f"whatsapp:{from_number}"

    def send_whatsapp(self, to: str, text: str) -> None:
        """`to` llega como +51...; Twilio necesita el prefijo whatsapp:."""
        self._client.messages.create(from_=self._from, to=f"whatsapp:{to}", body=text)
