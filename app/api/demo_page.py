"""Adaptador de entrada: la página de la demo para hablar con Lucía."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from app.api.payment_page import templates
from app.config import Settings, get_settings

router = APIRouter(tags=["demo"])


@router.get("/", response_class=HTMLResponse)
def demo_page(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> HTMLResponse:
    """Botón para llamar a la recepcionista desde el navegador."""
    if not settings.vapi_public_key or not settings.vapi_assistant_id:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Falta VAPI_PUBLIC_KEY o VAPI_ASSISTANT_ID en el .env.",
        )
    context = {
        "public_key": settings.vapi_public_key,
        "assistant_id": settings.vapi_assistant_id,
    }
    return templates.TemplateResponse(request, "demo.html", context)
