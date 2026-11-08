"""Métricas de la evaluación (T22): WER del reconocimiento de voz.

Uso:
  python -m scripts.eval_metrics                       # lista las últimas llamadas
  python -m scripts.eval_metrics CALL_ID "lo que dije" # calcula el WER
"""

import re
import sys
import unicodedata

from sqlmodel import Session, col, select

from app.adapters.sql_repository import CallRow, make_engine
from app.config import get_settings


def normalize(text: str) -> list[str]:
    """Minúsculas, sin tildes ni puntuación, y cada dígito por separado."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    words: list[str] = []
    for token in re.findall(r"[a-z]+|\d+", text):
        words.extend(list(token) if token.isdigit() else [token])
    return words


def word_error_rate(reference: str, hypothesis: str) -> float:
    """(sustituciones + borrados + inserciones) / palabras de la referencia."""
    ref, hyp = normalize(reference), normalize(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    previous = list(range(len(hyp) + 1))
    for i, ref_word in enumerate(ref, start=1):
        current = [i]
        for j, hyp_word in enumerate(hyp, start=1):
            cost = 0 if ref_word == hyp_word else 1
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            )
        previous = current
    return previous[-1] / len(ref)


def user_turns(transcript: str) -> str:
    """Solo lo que dijo el cliente: las líneas que empiezan con 'User:'."""
    return " ".join(
        line.removeprefix("User:").strip()
        for line in transcript.splitlines()
        if line.startswith("User:")
    )


def main() -> None:
    engine = make_engine(get_settings().database_url)
    with Session(engine) as session:
        if len(sys.argv) < 3:
            query = select(CallRow).order_by(col(CallRow.created_at).desc())
            for row in session.exec(query.limit(10)):
                print(f"{row.call_id}  {row.created_at:%d/%m %H:%M}  ${row.cost_usd}")
            return
        row = session.get(CallRow, sys.argv[1])
    if row is None:
        raise SystemExit(f"No encontré la llamada {sys.argv[1]}")
    heard = user_turns(row.transcript)
    print(f"Lo que entendió el ASR: {heard}")
    print(f"WER: {word_error_rate(sys.argv[2], heard):.1%}")


if __name__ == "__main__":
    main()
