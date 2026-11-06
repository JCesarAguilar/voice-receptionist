import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import get_settings
from app.container import get_tool_dispatcher
from app.main import app
from tests.test_booking import make_env
from tests.test_tool_dispatcher import make_dispatcher

SECRET = "secreto-de-prueba"


@pytest.fixture
def client():
    """La app real, pero con fakes en vez de Google, Twilio y Culqi."""
    dispatcher = make_dispatcher(make_env())
    app.dependency_overrides[get_tool_dispatcher] = lambda: dispatcher
    app.dependency_overrides[get_settings] = lambda: SimpleNamespace(
        vapi_tools_secret=SecretStr(SECRET)
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def vapi_payload(arguments) -> dict:
    return {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "call_9",
                    "type": "function",
                    "function": {
                        "name": "check_availability",
                        "arguments": arguments,
                    },
                }
            ],
        }
    }


ARGS = {"area": "laboral", "date": "2026-11-12"}


def test_without_secret_returns_401(client):
    response = client.post("/vapi/tools", json=vapi_payload(ARGS))

    assert response.status_code == 401


def test_wrong_secret_returns_401(client):
    response = client.post(
        "/vapi/tools", json=vapi_payload(ARGS), headers={"x-vapi-secret": "otro"}
    )

    assert response.status_code == 401


def test_valid_call_returns_vapi_format(client):
    response = client.post(
        "/vapi/tools", json=vapi_payload(ARGS), headers={"x-vapi-secret": SECRET}
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["toolCallId"] == "call_9"
    assert "Horarios libres" in result["result"]
    assert "error" not in result  # Vapi: result o error, nunca los dos


def test_arguments_as_json_text_are_accepted(client):
    payload = vapi_payload(json.dumps(ARGS))

    response = client.post(
        "/vapi/tools", json=payload, headers={"x-vapi-secret": SECRET}
    )

    assert "Horarios libres" in response.json()["results"][0]["result"]
