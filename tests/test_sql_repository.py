from datetime import timedelta
from uuid import uuid4

import pytest

from app.adapters.sql_repository import (
    SqlBookingRepository,
    SqlCallReportRepository,
    make_engine,
)
from app.domain.models import BookingStatus, CallReport
from tests.factories import LIMA, NOW, make_booking


@pytest.fixture
def database_url(tmp_path) -> str:
    """Un archivo de base nuevo y vacío para cada test."""
    return f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
def repo(database_url) -> SqlBookingRepository:
    return SqlBookingRepository(make_engine(database_url), LIMA)


def test_saves_and_reads_the_same_booking(repo):
    booking = make_booking(payment_order_id="ord-1", calendar_event_id="evt-1")

    repo.add(booking)

    assert repo.get(booking.id) == booking


def test_times_come_back_in_the_studio_timezone(repo):
    booking = make_booking()
    repo.add(booking)

    loaded = repo.get(booking.id)

    assert loaded is not None
    assert loaded.start.utcoffset() == timedelta(hours=-5)
    assert loaded.start.hour == 10


def test_missing_booking_returns_none(repo):
    assert repo.get(uuid4()) is None


def test_update_changes_the_status(repo):
    booking = make_booking()
    repo.add(booking)

    booking.expire()
    repo.update(booking)

    loaded = repo.get(booking.id)
    assert loaded is not None
    assert loaded.status == BookingStatus.EXPIRED


def test_finds_booking_by_payment_order(repo):
    booking = make_booking(payment_order_id="ord-77")
    repo.add(booking)

    found = repo.get_by_order_id("ord-77")

    assert found is not None
    assert found.id == booking.id
    assert repo.get_by_order_id("ord-no-existe") is None


def test_pending_created_before_filters_by_status_and_time(repo):
    old_pending = make_booking(created_at=NOW)
    new_pending = make_booking(created_at=NOW + timedelta(minutes=20))
    old_confirmed = make_booking(created_at=NOW)
    old_confirmed.confirm(NOW)
    for booking in (old_pending, new_pending, old_confirmed):
        repo.add(booking)

    result = repo.pending_created_before(NOW + timedelta(minutes=10))

    assert [b.id for b in result] == [old_pending.id]


def test_data_survives_a_restart(database_url):
    booking = make_booking()
    SqlBookingRepository(make_engine(database_url), LIMA).add(booking)

    restarted = SqlBookingRepository(make_engine(database_url), LIMA)

    assert restarted.get(booking.id) == booking


def test_call_report_saved_twice_is_updated_not_duplicated(database_url):
    repo = SqlCallReportRepository(make_engine(database_url))
    report = CallReport(
        call_id="call-1",
        ended_reason="customer-ended-call",
        duration_seconds=60,
        cost_usd=0.10,
        transcript="Hola",
        summary="",
        created_at=NOW,
    )

    repo.save(report)
    repo.save(report.model_copy(update={"cost_usd": 0.20}))

    saved = repo.get("call-1")
    assert saved is not None
    assert saved.cost_usd == 0.20
