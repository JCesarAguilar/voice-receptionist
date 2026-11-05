from datetime import date, time, timedelta

from app.domain.ports import TimeRange
from app.services.availability import AvailabilityService
from tests.factories import NOW, RULES, SATURDAY, THURSDAY, at
from tests.fakes import FakeCalendar, FixedClock

FRIDAY = date(2026, 11, 13)
MONDAY = date(2026, 11, 16)


def make_service(busy=None, now=NOW) -> AvailabilityService:
    return AvailabilityService(FakeCalendar(busy), FixedClock(now), RULES)


def test_free_day_without_preference_returns_first_three():
    result = make_service().find_slots(THURSDAY)

    assert result.slots == [at(THURSDAY, 9), at(THURSDAY, 10), at(THURSDAY, 11)]
    assert result.message == ""


def test_e2_busy_slot_offers_nearby_alternatives():
    busy = [TimeRange(at(THURSDAY, 10), at(THURSDAY, 10, 45))]

    result = make_service(busy).find_slots(THURSDAY, preferred_time=time(10, 0))

    assert at(THURSDAY, 10) not in result.slots
    assert result.slots == [at(THURSDAY, 9), at(THURSDAY, 11), at(THURSDAY, 12)]


def test_free_preferred_time_is_included():
    result = make_service().find_slots(THURSDAY, preferred_time=time(15, 0))

    assert result.slots == [at(THURSDAY, 14), at(THURSDAY, 15), at(THURSDAY, 16)]


def test_e3_saturday_proposes_monday():
    result = make_service().find_slots(SATURDAY, preferred_time=time(11, 0))

    assert all(slot.date() == MONDAY for slot in result.slots)
    assert "lunes a viernes" in result.message


def test_full_day_moves_to_next_day():
    busy = [TimeRange(at(THURSDAY, 9), at(THURSDAY, 18))]

    result = make_service(busy).find_slots(THURSDAY)

    assert result.slots[0] == at(FRIDAY, 9)
    assert "no hay horarios libres" in result.message


def test_respects_two_hours_advance():
    result = make_service(now=at(THURSDAY, 9, 30)).find_slots(THURSDAY)

    assert result.slots[0] == at(THURSDAY, 12)


def test_is_available():
    busy = [TimeRange(at(THURSDAY, 10), at(THURSDAY, 10, 45))]
    service = make_service(busy)

    assert service.is_available(at(THURSDAY, 11)) is True
    assert service.is_available(at(THURSDAY, 10)) is False
    assert service.is_available(at(THURSDAY, 10, 30)) is False


def test_past_day_starts_from_today():
    result = make_service().find_slots(NOW.date() - timedelta(days=5))

    assert result.slots[0].date() >= NOW.date()
