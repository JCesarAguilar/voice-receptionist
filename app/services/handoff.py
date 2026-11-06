"""Caso de uso: derivar la conversación a una persona del estudio."""

from app.domain.models import Area, Client, HandoffReason
from app.domain.ports import MessagingPort
from app.services import messages


class HandoffService:
    def __init__(self, messaging: MessagingPort, staff_whatsapp: str) -> None:
        self._messaging = messaging
        self._staff_whatsapp = staff_whatsapp

    def notify(
        self,
        *,
        reason: HandoffReason,
        client: Client,
        summary: str,
        area: Area | None = None,
    ) -> None:
        """Avisa al responsable por WhatsApp para que contacte al cliente."""
        text = messages.handoff_message(reason, client, summary, area)
        self._messaging.send_whatsapp(self._staff_whatsapp, text)
