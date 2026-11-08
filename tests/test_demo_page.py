from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)


def use_settings(**values):
    defaults = {"vapi_public_key": None, "vapi_assistant_id": None}
    settings = SimpleNamespace(**{**defaults, **values})
    app.dependency_overrides[get_settings] = lambda: settings


def test_demo_page_has_the_call_button_and_vapi_config():
    use_settings(vapi_public_key="pk-demo", vapi_assistant_id="asst-demo")
    try:
        html = client.get("/").text
    finally:
        app.dependency_overrides.clear()

    assert 'id="call-btn"' in html
    assert "pk-demo" in html and "asst-demo" in html


def test_demo_page_explains_missing_config():
    use_settings()
    try:
        response = client.get("/")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert "VAPI_PUBLIC_KEY" in response.json()["detail"]
