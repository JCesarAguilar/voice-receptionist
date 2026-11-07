from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.container import get_booking_service
from app.domain.models import format_soles
from app.main import app
from tests.test_booking import EMAIL, book, make_env, stored


@pytest.fixture
def env():
    env = make_env()
    app.dependency_overrides[get_booking_service] = lambda: env.service
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(
        culqi_public_key="pk_test_demo"
    )
    yield env
    app.dependency_overrides.clear()


@pytest.fixture
def client(env):
    return TestClient(app)


def test_pending_booking_shows_summary_and_checkout(env, client):
    booking = book(env)

    html = client.get(f"/pagar/{booking.id}").text

    assert format_soles(booking.price_cents) in html
    assert 'id="pay-form"' in html
    assert "pk_test_demo" in html


def test_paid_booking_shows_confirmation_without_checkout(env, client):
    booking = book(env)
    env.service.pay_with_token(booking.id, "tkn_test_1", EMAIL)

    html = client.get(f"/pagar/{booking.id}").text

    assert "ya está pagada" in html
    assert "checkout-js" not in html


def test_expired_booking_shows_notice(env, client):
    booking = stored(env, book(env))
    booking.expire()
    env.repository.update(booking)

    html = client.get(f"/pagar/{booking.id}").text

    assert "venció" in html
    assert 'id="pay-form"' not in html


def test_unknown_booking_returns_404(client):
    assert client.get(f"/pagar/{uuid4()}").status_code == 404
