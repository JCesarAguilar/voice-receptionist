"""Adaptadores de observabilidad: Langfuse, o nada si no está configurado."""

import logging
from typing import Any

from langfuse import Langfuse

from app.domain.models import CallReport

logger = logging.getLogger(__name__)


class LangfuseTracer:
    """Cada tool call es un span; todas las de una llamada comparten sesión."""

    def __init__(self, public_key: str, secret_key: str, host: str) -> None:
        self._client = Langfuse(public_key=public_key, secret_key=secret_key, host=host)

    def tool_call(
        self,
        *,
        call_id: str | None,
        name: str,
        arguments: dict[str, Any],
        output: str,
        ok: bool,
        seconds: float,
    ) -> None:
        try:
            with self._client.start_as_current_span(
                name=f"tool · {name}", input=arguments
            ) as span:
                span.update(
                    output=output,
                    level="DEFAULT" if ok else "ERROR",
                    metadata={"latency_ms": round(seconds * 1000)},
                )
                span.update_trace(name=f"tool · {name}", session_id=call_id)
        except Exception:
            logger.exception("No se pudo enviar la traza a Langfuse")

    def call_ended(self, report: CallReport) -> None:
        try:
            with self._client.start_as_current_span(
                name="llamada terminada", input=report.transcript
            ) as span:
                span.update(
                    output=report.summary or report.ended_reason,
                    metadata={
                        "ended_reason": report.ended_reason,
                        "duration_seconds": report.duration_seconds,
                        "cost_usd": report.cost_usd,
                    },
                )
                span.update_trace(name="llamada terminada", session_id=report.call_id)
        except Exception:
            logger.exception("No se pudo enviar el reporte a Langfuse")


class NoopTracer:
    """Se usa cuando no hay llaves de Langfuse: no registra nada."""

    def tool_call(
        self,
        *,
        call_id: str | None,
        name: str,
        arguments: dict[str, Any],
        output: str,
        ok: bool,
        seconds: float,
    ) -> None:
        return None

    def call_ended(self, report: CallReport) -> None:
        return None
