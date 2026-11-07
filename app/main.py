"""Punto de entrada de la API de la recepcionista de voz."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.payment_page import router as page_router
from app.api.payments import router as payments_router
from app.api.vapi_tools import router as vapi_router
from app.api.webhooks import router as webhooks_router
from app.config import get_settings
from app.container import get_booking_service
from app.jobs.expire_holds import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Al arrancar: valida la config y prende el job; al apagar, lo detiene."""
    get_settings()
    scheduler = start_scheduler(get_booking_service)
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Recepcionista de voz - Estudio Lex Andina", lifespan=lifespan)
app.include_router(vapi_router)
app.include_router(payments_router)
app.include_router(page_router)
app.include_router(webhooks_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Verifica que el servidor está vivo (lo usan ngrok y el deploy)."""
    return {"status": "ok"}
