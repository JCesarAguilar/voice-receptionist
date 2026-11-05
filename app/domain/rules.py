"""Reglas de horario del estudio: funciones puras, sin servicios externos."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class ScheduleRules:
    """Parámetros de la agenda. Vienen de la configuración, no del .env."""

    timezone: ZoneInfo
    opening_hour: int
    closing_hour: int
    consultation_minutes: int
    buffer_minutes: int
    min_advance_hours: int
    max_advance_days: int

    @property
    def consultation(self) -> timedelta:
        return timedelta(minutes=self.consultation_minutes)

    @property
    def slot_step(self) -> timedelta:
        """Distancia entre el inicio de un turno y el siguiente (consulta + margen)."""
        return timedelta(minutes=self.consultation_minutes + self.buffer_minutes)


class ScheduleRuleError(ValueError):
    """Un horario que no cumple las reglas. El mensaje se le puede decir al cliente."""


def is_business_day(day: date) -> bool:
    """Lunes (0) a viernes (4)."""
    return day.weekday() < 5


def candidate_slots(day: date, rules: ScheduleRules) -> list[datetime]:
    """Todos los turnos posibles de un día, sin mirar todavía el calendario."""
    if not is_business_day(day):
        return []

    midnight = datetime.combine(day, time(0), tzinfo=rules.timezone)
    start = midnight + timedelta(hours=rules.opening_hour)
    closing = midnight + timedelta(hours=rules.closing_hour)

    slots: list[datetime] = []
    while start + rules.consultation <= closing:
        slots.append(start)
        start += rules.slot_step
    return slots


def slot_end(start: datetime, rules: ScheduleRules) -> datetime:
    return start + rules.consultation


def validate_start(start: datetime, now: datetime, rules: ScheduleRules) -> None:
    """Lanza ScheduleRuleError si el horario no se puede reservar."""
    local = start.astimezone(rules.timezone)

    if not is_business_day(local.date()):
        raise ScheduleRuleError("El estudio atiende de lunes a viernes.")
    if local not in candidate_slots(local.date(), rules):
        raise ScheduleRuleError("Ese horario no es uno de los turnos de atención.")
    if start - now < timedelta(hours=rules.min_advance_hours):
        raise ScheduleRuleError(
            f"Las citas se reservan con al menos {rules.min_advance_hours} horas "
            "de anticipación."
        )
    if start - now > timedelta(days=rules.max_advance_days):
        raise ScheduleRuleError(
            f"Solo se puede reservar hasta {rules.max_advance_days} días adelante."
        )
