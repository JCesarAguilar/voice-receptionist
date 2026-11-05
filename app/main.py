"""Punto de entrada de la API de la recepcionista de voz."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Se ejecuta al arrancar: si falta una clave, la app no levanta."""
    get_settings()
    yield


app = FastAPI(title="Recepcionista de voz - Estudio Lex Andina", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    """Verifica que el servidor está vivo (lo usan ngrok y el deploy)."""
    return {"status": "ok"}
