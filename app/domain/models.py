"""Modelos del dominio: cómo es el negocio, sin depender de servicios externos."""

import re
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Area(StrEnum):
    CIVIL = "civil"
    PENAL = "penal"
    LABORAL = "laboral"
    FAMILIA = "familia"


class Modality(StrEnum):
    PRESENCIAL = "presencial"
    VIRTUAL = "virtual"


class BookingStatus(StrEnum):
    PENDING_PAYMENT = "pending_payment"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"


# Precios en céntimos (S/ 150.00 = 15000): el dinero nunca se guarda con decimales.
PRICES_CENTS: dict[Area, int] = {
    Area.CIVIL: 15000,
    Area.PENAL: 20000,
    Area.LABORAL: 12000,
    Area.FAMILIA: 15000,
}


def price_for(area: Area) -> int:
    """Precio de la consulta inicial del área, en céntimos."""
    return PRICES_CENTS[area]


def format_soles(cents: int) -> str:
    """Convierte céntimos a texto para hablar o escribir: 15000 -> 'S/ 150.00'."""
    return f"S/ {cents / 100:.2f}"


# Celular peruano en formato internacional: +51 seguido de 9 dígitos que empiezan en 9.
PERU_MOBILE = re.compile(r"^\+519\d{8}$")


class InvalidTransitionError(ValueError):
    """Un cambio de estado que el negocio no permite."""


class Client(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=100)
    whatsapp: str

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("whatsapp", mode="before")
    @classmethod
    def normalize_whatsapp(cls, value: str) -> str:
        """Acepta '+51 987 654 321' y lo guarda como '+51987654321'."""
        cleaned = re.sub(r"[\s\-()]", "", str(value))
        if not PERU_MOBILE.match(cleaned):
            raise ValueError("El WhatsApp debe ser un celular peruano: +51 9XX XXX XXX")
        return cleaned


class Booking(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    client: Client
    area: Area
    modality: Modality
    start: datetime
    end: datetime
    summary: str = Field(min_length=1, max_length=500)
    price_cents: int = Field(gt=0)
    status: BookingStatus = BookingStatus.PENDING_PAYMENT
    created_at: datetime
    calendar_event_id: str | None = None
    payment_order_id: str | None = None
    confirmed_at: datetime | None = None

    @field_validator("start", "end", "created_at")
    @classmethod
    def must_have_timezone(cls, value: datetime) -> datetime:
        """Una fecha sin zona horaria es ambigua: ¿hora de Lima o UTC?"""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("La fecha debe incluir zona horaria")
        return value

    @model_validator(mode="after")
    def end_after_start(self) -> "Booking":
        if self.end <= self.start:
            raise ValueError("La hora de fin debe ser posterior a la de inicio")
        return self

    def confirm(self, at: datetime) -> None:
        """Pasa a CONFIRMED. Solo desde PENDING_PAYMENT."""
        if self.status != BookingStatus.PENDING_PAYMENT:
            raise InvalidTransitionError("Solo se confirma una reserva pendiente.")
        self.status = BookingStatus.CONFIRMED
        self.confirmed_at = at

    def expire(self) -> None:
        """Pasa a EXPIRED. Solo desde PENDING_PAYMENT."""
        if self.status != BookingStatus.PENDING_PAYMENT:
            raise InvalidTransitionError("Solo vence una reserva pendiente.")
        self.status = BookingStatus.EXPIRED
