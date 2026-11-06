import pytest

from app.adapters.culqi import to_payment_status
from app.domain.ports import PaymentStatus


@pytest.mark.parametrize(
    ("culqi_state", "expected"),
    [
        ("created", PaymentStatus.PENDING),
        ("pending", PaymentStatus.PENDING),
        ("paid", PaymentStatus.PAID),
        ("expired", PaymentStatus.FAILED),
        ("deleted", PaymentStatus.FAILED),
        ("algo-nuevo", PaymentStatus.FAILED),
        (None, PaymentStatus.FAILED),
    ],
)
def test_culqi_states_are_translated_safely(culqi_state, expected):
    assert to_payment_status(culqi_state) == expected
