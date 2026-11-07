import httpx2
import pytest

from app.adapters.culqi import CulqiError, CulqiPayments
from tests.factories import make_booking


def payments_answering(status: int, body: dict) -> tuple[CulqiPayments, list]:
    """Un CulqiPayments que no sale a internet: responde lo que le digamos."""
    sent: list[httpx2.Request] = []

    def answer(request: httpx2.Request) -> httpx2.Response:
        sent.append(request)
        return httpx2.Response(status, json=body)

    transport = httpx2.MockTransport(answer)
    return CulqiPayments("sk_test_x", 30, transport=transport), sent


def test_approved_charge_returns_true_and_sends_the_right_data():
    payments, sent = payments_answering(201, {"object": "charge", "id": "chr_test"})
    booking = make_booking()

    assert payments.charge(booking, "tkn_test_1", "ana@example.com") is True

    body = sent[0].read().decode()
    assert sent[0].url.path == "/v2/charges"
    assert '"source_id":"tkn_test_1"' in body.replace(" ", "")
    assert '"amount":12000' in body.replace(" ", "")


def test_declined_card_returns_false():
    payments, _ = payments_answering(402, {"object": "error", "type": "card_error"})

    assert payments.charge(make_booking(), "tkn_test_1", "ana@example.com") is False


def test_system_error_raises_culqi_error():
    payments, _ = payments_answering(401, {"object": "error"})

    with pytest.raises(CulqiError, match="401"):
        payments.charge(make_booking(), "tkn_test_1", "ana@example.com")
