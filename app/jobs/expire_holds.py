"""Tarea programada: cada minuto vence las reservas que no se pagaron."""

import logging
from collections.abc import Callable

from apscheduler.schedulers.background import BackgroundScheduler

from app.services.booking import BookingService

logger = logging.getLogger(__name__)


def expire_holds(service: BookingService) -> int:
    """Una pasada del job. Si falla, se registra y se intenta al minuto."""
    try:
        expired = service.expire_overdue()
    except Exception:
        logger.exception("Falló la expiración de reservas")
        return 0
    if expired:
        logger.info("Reservas vencidas: %s", expired)
    return expired


def start_scheduler(
    get_service: Callable[[], BookingService], every_seconds: int = 60
) -> BackgroundScheduler:
    """Arranca el reloj en un hilo aparte; la API sigue atendiendo."""
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        lambda: expire_holds(get_service()),
        "interval",
        seconds=every_seconds,
        id="expire_holds",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    return scheduler
