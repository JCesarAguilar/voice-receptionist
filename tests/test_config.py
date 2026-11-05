import pytest
from pydantic import ValidationError

from app.config import Settings

VALID_ENV = {
    "VAPI_TOOLS_SECRET": "secret",
    "GOOGLE_CALENDAR_ID": "cal@group.calendar.google.com",
    "GOOGLE_SERVICE_ACCOUNT_FILE": "credentials/sa.json",
    "CULQI_PUBLIC_KEY": "pk_test_x",
    "CULQI_SECRET_KEY": "sk_test_x",
    "TWILIO_ACCOUNT_SID": "ACx",
    "TWILIO_AUTH_TOKEN": "token",
    "TWILIO_WHATSAPP_FROM": "whatsapp:+14155238886",
    "HANDOFF_WHATSAPP_TO": "whatsapp:+51999999999",
    "LANGFUSE_PUBLIC_KEY": "pk-lf-x",
    "LANGFUSE_SECRET_KEY": "sk-lf-x",
    "PUBLIC_BASE_URL": "https://example.ngrok-free.app",
}


@pytest.fixture
def valid_env(monkeypatch):
    for key, value in VALID_ENV.items():
        monkeypatch.setenv(key, value)


def test_loads_with_all_keys_and_spec_defaults(valid_env):
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.timezone == "America/Lima"
    assert settings.consultation_minutes == 45
    assert settings.payment_hold_minutes == 30


def test_secrets_are_hidden_when_printed(valid_env):
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert "sk_test_x" not in str(settings)
    assert settings.culqi_secret_key.get_secret_value() == "sk_test_x"


def test_missing_key_names_the_field(valid_env, monkeypatch):
    monkeypatch.delenv("CULQI_SECRET_KEY")

    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None)  # type: ignore[call-arg]

    assert "culqi_secret_key" in str(error.value)
