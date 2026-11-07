from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.container import get_booking_service
from app.domain.models import BookingStatus
from app.main import app
from tests.test_booking import EMAIL, book, make_env, stored


@pytest.fixture
def env():
    """La app real, con el BookingService armado sobre fakes."""
    env = make_env()
    app.dependency_overrides[get_booking_service] = lambda: env.service
    yield env
    app.dependency_overrides.clear()


@pytest.fixture
def client(env):
    return TestClient(app)


def test_order_is_created_once_even_if_page_reloads(env, client):
    booking = book(env)
    url = f"/payments/{booking.id}/order"

    first = client.post(url, json={"email": EMAIL})
    second = client.post(url, json={"email": EMAIL})

    assert first.status_code == 200
    assert first.json() == second.json() == {"order_id": "ord-1"}


def test_approved_charge_confirms_the_booking(env, client):
    booking = book(env)

    response = client.post(
        f"/payments/{booking.id}/charge",
        json={"token_id": "tkn_test_1", "email": EMAIL},
    )

    assert response.json() == {"paid": True}
    assert stored(env, booking).status == BookingStatus.CONFIRMED


def test_declined_charge_keeps_the_booking_pending(env, client):
    env.payments.approve_charges = False
    booking = book(env)

    response = client.post(
        f"/payments/{booking.id}/charge",
        json={"token_id": "tkn_test_1", "email": EMAIL},
    )

    assert response.json() == {"paid": False}
    assert stored(env, booking).status == BookingStatus.PENDING_PAYMENT


def test_expired_booking_cannot_be_paid(env, client):
    booking = stored(env, book(env))
    booking.expire()
    env.repository.update(booking)

    response = client.post(f"/payments/{booking.id}/order", json={"email": EMAIL})

    assert response.status_code == 409


def test_unknown_booking_returns_409(client):
    response = client.post(f"/payments/{uuid4()}/order", json={"email": EMAIL})

    assert response.status_code == 409


def test_invalid_email_is_rejected_before_reaching_culqi(env, client):
    booking = book(env)

    response = client.post(
        f"/payments/{booking.id}/order", json={"email": "no-es-un-email"}
    )

    assert response.status_code == 422
    assert env.payments.orders == {}
