from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest

from app.domain.rules import (
    ScheduleRuleError,
    candidate_slots,
    slot_end,
    validate_start,
)
from tests.factories import NOW, RULES, SATURDAY, THURSDAY, at


def test_weekday_has_nine_slots_from_9_to_17():
    slots = candidate_slots(THURSDAY, RULES)

    assert len(slots) == 9
    assert slots[0] == at(THURSDAY, 9)
    assert slots[-1] == at(THURSDAY, 17)


def test_saturday_has_no_slots():
    assert candidate_slots(SATURDAY, RULES) == []


def test_slot_end_adds_consultation_minutes():
    assert slot_end(at(THURSDAY, 10), RULES) == at(THURSDAY, 10, 45)


def test_valid_slot_passes():
    validate_start(at(THURSDAY, 10), NOW, RULES)  # no lanza error


def test_utc_time_is_converted_to_lima():
    ten_am_lima_in_utc = at(THURSDAY, 10).astimezone(ZoneInfo("UTC"))

    validate_start(ten_am_lima_in_utc, NOW, RULES)


def test_rejects_saturday():
    with pytest.raises(ScheduleRuleError, match="lunes a viernes"):
        validate_start(at(SATURDAY, 11), NOW, RULES)


def test_rejects_time_that_is_not_a_slot():
    with pytest.raises(ScheduleRuleError, match="turnos"):
        validate_start(at(THURSDAY, 10, 30), NOW, RULES)


def test_rejects_less_than_two_hours_ahead():
    now = at(THURSDAY, 9, 30)

    with pytest.raises(ScheduleRuleError, match="anticipación"):
        validate_start(at(THURSDAY, 10), now, RULES)


def test_rejects_more_than_30_days_ahead():
    far = at(THURSDAY, 10) + timedelta(days=35)

    with pytest.raises(ScheduleRuleError):
        validate_start(far, NOW, RULES)
