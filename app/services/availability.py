"""Caso de uso: encontrar horarios libres para proponer al cliente."""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from app.domain.ports import CalendarPort, Clock, TimeRange
from app.domain.rules import (
    ScheduleRuleError,
    ScheduleRules,
    candidate_slots,
    is_business_day,
    slot_end,
    validate_start,
)


@dataclass(frozen=True)
class AvailabilityResult:
    """Horarios a proponer y, si hace falta, una explicación para el cliente."""

    slots: list[datetime] = field(default_factory=list)
    message: str = ""


def _overlaps(start: datetime, end: datetime, busy: list[TimeRange]) -> bool:
    return any(r.start < end and r.end > start for r in busy)


def _minutes_of_day(value: datetime | time) -> int:
    return value.hour * 60 + value.minute


class AvailabilityService:
    def __init__(
        self,
        calendar: CalendarPort,
        clock: Clock,
        rules: ScheduleRules,
        max_options: int = 3,
    ) -> None:
        self._calendar = calendar
        self._clock = clock
        self._rules = rules
        self._max_options = max_options

    def find_slots(
        self, day: date, preferred_time: time | None = None
    ) -> AvailabilityResult:
        """Hasta `max_options` horarios libres, empezando por el día pedido."""
        now = self._clock.now()
        day = max(day, now.astimezone(self._rules.timezone).date())
        notes: list[str] = []
        if not is_business_day(day):
            notes.append("El estudio atiende de lunes a viernes.")

        for offset in range(self._rules.max_advance_days + 1):
            current = day + timedelta(days=offset)
            free = self._free_slots(current, now)
            if not free:
                continue
            if offset > 0 and is_business_day(day):
                notes.append("Ese día no hay horarios libres.")
            chosen = self._closest(free, preferred_time)
            return AvailabilityResult(slots=chosen, message=" ".join(notes))

        return AvailabilityResult(
            message="No hay horarios libres en los próximos días."
        )

    def is_available(self, start: datetime) -> bool:
        """¿Se puede reservar este horario ahora? Lo usa la reserva antes de crear."""
        if not self._is_bookable(start, self._clock.now()):
            return False
        end = slot_end(start, self._rules)
        return not _overlaps(start, end, self._calendar.busy_ranges(start, end))

    def _free_slots(self, day: date, now: datetime) -> list[datetime]:
        candidates = candidate_slots(day, self._rules)
        if not candidates:
            return []
        busy = self._calendar.busy_ranges(
            candidates[0], slot_end(candidates[-1], self._rules)
        )
        return [
            slot
            for slot in candidates
            if self._is_bookable(slot, now)
            and not _overlaps(slot, slot_end(slot, self._rules), busy)
        ]

    def _is_bookable(self, start: datetime, now: datetime) -> bool:
        try:
            validate_start(start, now, self._rules)
        except ScheduleRuleError:
            return False
        return True

    def _closest(
        self, slots: list[datetime], preferred_time: time | None
    ) -> list[datetime]:
        if preferred_time is None:
            return slots[: self._max_options]
        target = _minutes_of_day(preferred_time)
        nearest = sorted(slots, key=lambda s: abs(_minutes_of_day(s) - target))
        return sorted(nearest[: self._max_options])
