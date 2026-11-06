"""Adaptador de salida: la hora real del sistema."""

from datetime import datetime
from zoneinfo import ZoneInfo


class SystemClock:
    """Cumple el puerto Clock. En los tests se usa FixedClock."""

    def __init__(self, timezone: ZoneInfo) -> None:
        self._timezone = timezone

    def now(self) -> datetime:
        return datetime.now(self._timezone)
