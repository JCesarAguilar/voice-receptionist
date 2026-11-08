"""Adaptador de entrada: el endpoint HTTP que llama Vapi en cada tool call."""

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.tool_dispatcher import ToolDispatcher
from app.config import Settings, get_settings
from app.container import get_tool_dispatcher
from app.schemas.tools import VapiToolRequest, VapiToolResponse

router = APIRouter(prefix="/vapi", tags=["vapi"])


def verify_vapi_secret(
    settings: Annotated[Settings, Depends(get_settings)],
    x_vapi_secret: Annotated[str | None, Header()] = None,
) -> None:
    """Solo Vapi conoce el secreto: sin él, nadie puede usar las tools."""
    expected = settings.vapi_tools_secret.get_secret_value()
    if x_vapi_secret is None or not secrets.compare_digest(x_vapi_secret, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Secreto inválido.")


@router.post(
    "/tools",
    response_model=VapiToolResponse,
    response_model_exclude_none=True,
    dependencies=[Depends(verify_vapi_secret)],
)
def handle_tool_calls(
    request: VapiToolRequest,
    dispatcher: Annotated[ToolDispatcher, Depends(get_tool_dispatcher)],
) -> VapiToolResponse:
    """Ejecuta cada tool call y responde en el formato que espera Vapi."""
    call_id = request.message.call.id if request.message.call else None
    results = [dispatcher.run(call, call_id) for call in request.message.tool_call_list]
    return VapiToolResponse(results=results)
