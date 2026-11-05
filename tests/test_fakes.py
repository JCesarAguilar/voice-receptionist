from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.domain.ports import TimeRange
from tests.fakes import FakeCalendar, InMemoryBookingRepository
from tests.test_models import make_booking

LIMA = ZoneInfo("America/Lima")


def test_calendar_returns_only_overlapping_ranges():
    nine = datetime(2026, 11, 12, 9, 0, tzinfo=LIMA)
    calendar = FakeCalendar(busy=[TimeRange(nine, nine + timedelta(minutes=45))])

    assert calendar.busy_ranges(nine, nine + timedelta(hours=1)) != []
    assert (
        calendar.busy_ranges(nine + timedelta(hours=2), nine + timedelta(hours=3)) == []
    )


def test_created_hold_becomes_busy():
    calendar = FakeCalendar()
    booking = make_booking()

    calendar.create_hold(booking)

    assert calendar.busy_ranges(booking.start, booking.end) != []


def test_repository_returns_copies_like_a_real_database():
    repo = InMemoryBookingRepository()
    booking = make_booking()
    repo.add(booking)

    loaded = repo.get(booking.id)
    assert loaded is not None
    loaded.summary = "cambiado sin update"

    reloaded = repo.get(booking.id)
    assert reloaded is not None
    assert reloaded.summary == "Despido sin aviso"
