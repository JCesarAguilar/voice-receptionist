from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import get_settings
from app.container import get_call_log_service
from app.main import app
from app.services.calls import CallLogService
from tests.factories import NOW
from tests.fakes import FixedClock, InMemoryCallReportRepository, RecordingTracer

SECRET = "secreto-de-prueba"
HEADERS = {"x-vapi-secret": SECRET}
URL = "/webhooks/vapi"


@pytest.fixture
def fakes():
    repository = InMemoryCallReportRepository()
    tracer = RecordingTracer()
    service = CallLogService(repository, tracer, FixedClock(NOW))
    app.dependency_overrides[get_call_log_service] = lambda: service
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(
        vapi_tools_secret=SecretStr(SECRET)
    )
    yield repository, tracer
    app.dependency_overrides.clear()


def report(**overrides) -> dict:
    message = {
        "type": "end-of-call-report",
        "call": {"id": "call-123"},
        "endedReason": "customer-ended-call",
        "cost": 0.12,
        "durationSeconds": 95,
        "artifact": {"transcript": "AI: Hola\nUser: Quiero una cita"},
        "analysis": {"summary": "El cliente agendó una consulta laboral."},
    }
    message.update(overrides)
    return {"message": message}


def test_report_is_saved_and_traced(fakes):
    repository, tracer = fakes

    response = TestClient(app).post(URL, json=report(), headers=HEADERS)

    assert response.json() == {"status": "saved"}
    saved = repository.reports["call-123"]
    assert saved.cost_usd == 0.12
    assert saved.duration_seconds == 95
    assert "Quiero una cita" in saved.transcript
    assert tracer.ended == [saved]


def test_other_messages_are_ignored(fakes):
    repository, _ = fakes

    response = TestClient(app).post(
        URL, json=report(type="status-update"), headers=HEADERS
    )

    assert response.json() == {"status": "ignored"}
    assert repository.reports == {}


def test_missing_cost_and_duration_are_saved_as_zero(fakes):
    repository, _ = fakes

    TestClient(app).post(
        URL, json=report(cost=None, durationSeconds=None), headers=HEADERS
    )

    assert repository.reports["call-123"].cost_usd == 0


def test_without_secret_returns_401(fakes):
    assert TestClient(app).post(URL, json=report()).status_code == 401
