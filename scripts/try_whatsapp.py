"""Prueba manual del adaptador de WhatsApp (T11).

Uso: python -m scripts.try_whatsapp
"""

from app.adapters.twilio_whatsapp import TwilioWhatsApp
from app.config import get_settings


def main() -> None:
    settings = get_settings()
    whatsapp = TwilioWhatsApp(
        settings.twilio_account_sid,
        settings.twilio_auth_token.get_secret_value(),
        settings.twilio_whatsapp_from,
    )
    whatsapp.send_whatsapp(
        settings.handoff_whatsapp_to,
        "Hola, soy la recepcionista del Estudio Lex Andina. "
        "Si lees esto, el adaptador de WhatsApp funciona (T11).",
    )
    print("Mensaje enviado. Revisa tu WhatsApp.")


if __name__ == "__main__":
    main()
