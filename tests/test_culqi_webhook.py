import json

import pytest
from fastapi.testclient import TestClient

from app.container import get_booking_service
from app.domain.models import BookingStatus
from app.main import app
from tests.test_booking import book, make_env, open_payment_page, stored

URL = "/webhooks/culqi"


@pytest.fixture
def env():
    env = make_env()
    app.dependency_overrides[get_booking_service] = lambda: env.service
    yield env
    app.dependency_overrides.clear()


@pytest.fixture
def client(env):
    return TestClient(app)


def order_event(order_id: str, as_text: bool = False) -> dict:
    order = {"object": "order", "id": order_id, "state": "paid"}
    data = json.dumps(order) if as_text else order
    return {"object": "event", "type": "order.status.changed", "data": data}


def test_paid_order_confirms_and_repeated_notice_sends_nothing_new(env, client):
    booking = book(env)
    order_id = open_payment_page(env, booking)
    env.payments.mark_paid(order_id)

    first = client.post(URL, json=order_event(order_id))
    messages_after_first = len(env.messaging.sent)
    client.post(URL, json=order_event(order_id))

    assert first.json() == {"status": "processed"}
    assert stored(env, booking).status == BookingStatus.CONFIRMED
    assert len(env.messaging.sent) == messages_after_first


def test_data_sent_as_json_text_also_works(env, client):
    booking = book(env)
    order_id = open_payment_page(env, booking)
    env.payments.mark_paid(order_id)

    client.post(URL, json=order_event(order_id, as_text=True))

    assert stored(env, booking).status == BookingStatus.CONFIRMED


def test_fake_notice_for_unpaid_order_does_not_confirm(env, client):
    booking = book(env)
    order_id = open_payment_page(env, booking)  # Culqi dice: aún sin pagar

    client.post(URL, json=order_event(order_id))

    assert stored(env, booking).status == BookingStatus.PENDING_PAYMENT


def test_other_event_types_are_ignored(client):
    event = {"type": "charge.creation.succeeded", "data": {"object": "charge"}}

    assert client.post(URL, json=event).json() == {"status": "ignored"}


def test_unknown_order_is_reported(client):
    response = client.post(URL, json=order_event("ord_test_no_existe"))

    assert response.json() == {"status": "unknown_order"}
