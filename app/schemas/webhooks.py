"""El aviso (evento) que Culqi envía a nuestro webhook."""

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.tools import VapiCall


class CulqiEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    data: dict[str, Any] | str

    def order_id(self) -> str | None:
        """El id de la orden, si el evento trae una. Si no, None."""
        data = self.data
        if isinstance(data, str):  # Culqi a veces manda `data` como texto JSON
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return None
        if not isinstance(data, dict) or data.get("object") != "order":
            return None
        order_id = data.get("id")
        return order_id if isinstance(order_id, str) else None


class VapiArtifact(BaseModel):
    model_config = ConfigDict(extra="ignore")

    transcript: str = ""


class VapiAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")

    summary: str = ""


class VapiServerMessage(BaseModel):
    """Un aviso de Vapi. Solo nos interesa el `end-of-call-report`."""

    model_config = ConfigDict(extra="ignore")

    type: str
    call: VapiCall | None = None
    ended_reason: str = Field(default="", alias="endedReason")
    cost: float | None = None
    duration_seconds: float | None = Field(default=None, alias="durationSeconds")
    transcript: str = ""
    summary: str = ""
    artifact: VapiArtifact | None = None
    analysis: VapiAnalysis | None = None

    def full_transcript(self) -> str:
        """Vapi la manda arriba o dentro de `artifact`, según la versión."""
        if self.transcript:
            return self.transcript
        return self.artifact.transcript if self.artifact else ""

    def call_summary(self) -> str:
        """Igual: arriba o dentro de `analysis`."""
        if self.summary:
            return self.summary
        return self.analysis.summary if self.analysis else ""


class VapiServerRequest(BaseModel):
    message: VapiServerMessage
