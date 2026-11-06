"""Contratos del endpoint /vapi/tools: lo que manda Vapi y lo que respondemos."""

import datetime as dt
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.models import Area, HandoffReason, Modality

# --- El sobre que manda Vapi ---


class ToolFunction(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)

    @field_validator("arguments", mode="before")
    @classmethod
    def parse_json_text(cls, value: Any) -> Any:
        """Vapi puede mandar los argumentos como objeto o como texto JSON."""
        if isinstance(value, str):
            return json.loads(value) if value.strip() else {}
        return value


class ToolCall(BaseModel):
    id: str
    function: ToolFunction


class VapiMessage(BaseModel):
    type: str
    tool_call_list: list[ToolCall] = Field(default_factory=list, alias="toolCallList")


class VapiToolRequest(BaseModel):
    message: VapiMessage


# --- Lo que respondemos ---


class ToolResult(BaseModel):
    """Una respuesta por tool call. Lleva `result` o `error`, nunca los dos."""

    tool_call_id: str = Field(serialization_alias="toolCallId")
    result: str | None = None
    error: str | None = None


class VapiToolResponse(BaseModel):
    results: list[ToolResult]


# --- Los argumentos de cada tool ---


class CheckAvailabilityArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")

    area: Area
    date: dt.date
    preferred_time: dt.time | None = None


class CreateBookingArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")

    area: Area
    start: dt.datetime
    modality: Modality
    client_name: str
    client_whatsapp: str
    summary: str = Field(min_length=1, max_length=500)


class HandoffArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reason: HandoffReason
    client_name: str
    client_whatsapp: str
    summary: str
    area: Area | None = None
