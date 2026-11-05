"""Punto de entrada de la API de la recepcionista de voz."""

from fastapi import FastAPI

app = FastAPI(title="Recepcionista de voz - Estudio Lex Andina")


@app.get("/health")
def health() -> dict[str, str]:
    """Verifica que el servidor está vivo (lo usan ngrok y el deploy)."""
    return {"status": "ok"}