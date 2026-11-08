"""Crea o actualiza el asistente de Vapi desde los archivos versionados (T19).

Uso: python -m scripts.sync_vapi_assistant
La primera vez crea el asistente e imprime su id; guárdalo en el .env como
VAPI_ASSISTANT_ID para que las siguientes veces lo actualice.
"""

import json
from pathlib import Path

import httpx2

from app.config import get_settings

VAPI_API = "https://api.vapi.ai"
ASSISTANT_DIR = Path(__file__).resolve().parents[1] / "assistant"
FIRST_MESSAGE = (
    "Hola, gracias por comunicarte con el Estudio Lex Andina. "
    "Soy Lucía, ¿en qué te puedo ayudar?"
)
# Palabras que el reconocimiento de voz debe priorizar (palabra:peso).
KEYWORDS = ["Lex:3", "Andina:3", "laboral:2", "penal:2", "presencial:2"]


def build_prompt() -> str:
    prompt = (ASSISTANT_DIR / "system_prompt.md").read_text(encoding="utf-8")
    estudio = (ASSISTANT_DIR / "estudio.md").read_text(encoding="utf-8")
    return f"{prompt}\n\n# Información del estudio\n{estudio}"


def build_tools(tools_url: str, secret: str) -> list[dict]:
    tools = json.loads((ASSISTANT_DIR / "tools.json").read_text(encoding="utf-8"))
    server = {"url": tools_url, "headers": {"x-vapi-secret": secret}}
    return [{**tool, "server": server} for tool in tools]


def build_assistant() -> dict:
    settings = get_settings()
    tools_url = f"{settings.public_base_url}/vapi/tools"
    secret = settings.vapi_tools_secret.get_secret_value()
    return {
        "name": "Lucia - Estudio Lex Andina",
        "firstMessage": FIRST_MESSAGE,
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.3,
            "messages": [{"role": "system", "content": build_prompt()}],
            "tools": build_tools(tools_url, secret),
        },
        "voice": {"provider": "azure", "voiceId": "es-PE-CamilaNeural"},
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "es",
            "keywords": KEYWORDS,
        },
    }


def main() -> None:
    settings = get_settings()
    if settings.vapi_api_key is None:
        raise SystemExit("Falta VAPI_API_KEY en el .env")
    token = settings.vapi_api_key.get_secret_value()
    headers = {"Authorization": f"Bearer {token}"}
    assistant_id = settings.vapi_assistant_id
    with httpx2.Client(base_url=VAPI_API, headers=headers, timeout=30) as http:
        if assistant_id:
            response = http.patch(f"/assistant/{assistant_id}", json=build_assistant())
        else:
            response = http.post("/assistant", json=build_assistant())
    if response.is_error:
        raise SystemExit(f"Vapi respondió {response.status_code}: {response.text}")
    print(f"Asistente listo: {response.json()['id']}")
    if not assistant_id:
        print("Guárdalo en el .env como VAPI_ASSISTANT_ID.")


if __name__ == "__main__":
    main()
