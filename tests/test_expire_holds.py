from datetime import timedelta

from app.domain.models import BookingStatus
from app.jobs.expire_holds import expire_holds
from tests.test_booking import book, make_env, stored


def test_job_expires_unpaid_bookings_after_the_hold():
    env = make_env()
    booking = book(env)
    env.clock.advance(timedelta(minutes=31))

    assert expire_holds(env.service) == 1
    assert stored(env, booking).status == BookingStatus.EXPIRED


def test_job_does_nothing_before_the_hold_ends():
    env = make_env()
    book(env)
    env.clock.advance(timedelta(minutes=29))

    assert expire_holds(env.service) == 0


class BrokenService:
    def expire_overdue(self) -> int:
        raise RuntimeError("Google no responde")


def test_job_survives_errors():
    assert expire_holds(BrokenService()) == 0  # type: ignore[arg-type]
