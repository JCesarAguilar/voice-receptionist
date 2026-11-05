"""Configuración de la app: lee el .env y lo valida al arrancar."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Claves y reglas de negocio. Sin valor por defecto = obligatorio."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Secretos y conexiones (obligatorios) ---
    vapi_tools_secret: SecretStr
    google_calendar_id: str
    google_service_account_file: str
    culqi_public_key: str
    culqi_secret_key: SecretStr
    twilio_account_sid: str
    twilio_auth_token: SecretStr
    twilio_whatsapp_from: str
    handoff_whatsapp_to: str
    langfuse_public_key: str
    langfuse_secret_key: SecretStr
    langfuse_base_url: str = "https://cloud.langfuse.com"
    public_base_url: str

    # --- Reglas de negocio (Spec, sección 5) ---
    timezone: str = "America/Lima"
    opening_hour: int = Field(default=9, ge=0, le=23)
    closing_hour: int = Field(default=18, ge=1, le=24)
    consultation_minutes: int = Field(default=45, gt=0)
    buffer_minutes: int = Field(default=15, ge=0)
    min_advance_hours: int = Field(default=2, ge=0)
    max_advance_days: int = Field(default=30, gt=0)
    payment_hold_minutes: int = Field(default=30, gt=0)
    max_slot_options: int = Field(default=3, gt=0)


@lru_cache
def get_settings() -> Settings:
    """Crea la configuración una sola vez y la reutiliza en toda la app."""
    return Settings()  # type: ignore[call-arg]  # los valores vienen del .env
