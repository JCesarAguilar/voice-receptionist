"""Prueba manual del adaptador de Culqi (T12).

Uso: python -m scripts.try_culqi
"""

from datetime import datetime, timedelta

from app.adapters.culqi import CulqiPayments
from app.config import get_schedule_rules, get_settings
from app.domain.models import Area, Booking, Client, Modality, price_for
from app.domain.rules import slot_end


def main() -> None:
    settings = get_settings()
    rules = get_schedule_rules()
    payments = CulqiPayments(
        settings.culqi_secret_key.get_secret_value(),
        settings.payment_hold_minutes,
    )

    now = datetime.now(rules.timezone)
    start = now.replace(hour=10, minute=0, second=0, microsecond=0)
    start += timedelta(days=1)
    booking = Booking(
        client=Client(name="Prueba Culqi", whatsapp="+51999999999"),
        area=Area.LABORAL,
        modality=Modality.VIRTUAL,
        start=start,
        end=slot_end(start, rules),
        summary="Orden de prueba del adaptador",
        price_cents=price_for(Area.LABORAL),
        created_at=now,
    )

    order_id = payments.create_order(booking, "prueba@example.com")
    print(f"1. Orden creada: {order_id}")
    print(f"2. Estado según Culqi: {payments.get_status(order_id)}")
    print("3. Búscala en el panel de Culqi, en modo integración.")


if __name__ == "__main__":
    main()
