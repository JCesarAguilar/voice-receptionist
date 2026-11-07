from pathlib import Path

from app.domain.models import PRICES_CENTS, HandoffReason, format_soles

ASSISTANT = Path(__file__).resolve().parents[1] / "assistant"
ESTUDIO = (ASSISTANT / "estudio.md").read_text(encoding="utf-8")
PROMPT = (ASSISTANT / "system_prompt.md").read_text(encoding="utf-8")


def test_estudio_prices_match_the_code():
    for area, cents in PRICES_CENTS.items():
        assert f"{area.value.capitalize()}: {format_soles(cents)}" in ESTUDIO


def test_prompt_uses_the_handoff_reasons_the_backend_accepts():
    for reason in (
        HandoffReason.URGENT,
        HandoffReason.CLIENT_REQUEST,
        HandoffReason.NOT_UNDERSTOOD,
    ):
        assert f'"{reason.value}"' in PROMPT


def test_prompt_mentions_every_tool():
    for tool in ("check_availability", "create_booking", "handoff_to_human"):
        assert f"`{tool}`" in PROMPT
