"""Caso de uso: registrar cómo terminó cada llamada (criterio A9 de la Spec)."""

from app.domain.models import CallReport
from app.domain.ports import CallReportRepository, Clock, Tracer


class CallLogService:
    def __init__(
        self, repository: CallReportRepository, tracer: Tracer, clock: Clock
    ) -> None:
        self._repository = repository
        self._tracer = tracer
        self._clock = clock

    def record(
        self,
        *,
        call_id: str,
        ended_reason: str,
        duration_seconds: float,
        cost_usd: float,
        transcript: str,
        summary: str,
    ) -> CallReport:
        """Guarda el reporte en la base y lo envía a la observabilidad."""
        report = CallReport(
            call_id=call_id,
            ended_reason=ended_reason,
            duration_seconds=duration_seconds,
            cost_usd=cost_usd,
            transcript=transcript,
            summary=summary,
            created_at=self._clock.now(),
        )
        self._repository.save(report)
        self._tracer.call_ended(report)
        return report
