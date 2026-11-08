"""Configuración de la app: lee el .env y lo valida al arrancar."""

from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.rules import ScheduleRules


class Settings(BaseSettings):
    """Claves y reglas de negocio. Sin valor por defecto = obligatorio."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Secretos y conexiones (obligatorios) ---
    vapi_tools_secret: SecretStr
    vapi_api_key: SecretStr | None = None
    vapi_assistant_id: str | None = None
    google_calendar_id: str
    google_service_account_file: str
    culqi_public_key: str
    culqi_secret_key: SecretStr
    twilio_account_sid: str
    twilio_auth_token: SecretStr
    twilio_whatsapp_from: str
    handoff_whatsapp_to: str
    langfuse_public_key: str | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: str = "https://cloud.langfuse.com"
    public_base_url: str
    database_url: str = "sqlite:///receptionist.db"
    office_address: str = "Av. Larco 123, Miraflores, Lima"
    vapi_public_key: str | None = None

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

    @field_validator("culqi_secret_key")
    @classmethod
    def no_live_keys(cls, value: SecretStr) -> SecretStr:
        """En desarrollo solo se aceptan llaves de prueba de Culqi."""
        if value.get_secret_value().startswith("sk_live_"):
            raise ValueError("Este proyecto solo acepta llaves de prueba (sk_test_).")
        return value


@lru_cache
def get_settings() -> Settings:
    """Crea la configuración una sola vez y la reutiliza en toda la app."""
    return Settings()  # type: ignore[call-arg]  # los valores vienen del .env


def get_schedule_rules() -> ScheduleRules:
    """Traduce la configuración a las reglas que entiende el dominio."""
    settings = get_settings()
    return ScheduleRules(
        timezone=ZoneInfo(settings.timezone),
        opening_hour=settings.opening_hour,
        closing_hour=settings.closing_hour,
        consultation_minutes=settings.consultation_minutes,
        buffer_minutes=settings.buffer_minutes,
        min_advance_hours=settings.min_advance_hours,
        max_advance_days=settings.max_advance_days,
    )
