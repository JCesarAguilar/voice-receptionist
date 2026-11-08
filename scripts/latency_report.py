"""Latencias de la evaluación (T22): respuesta percibida (Vapi) y tools (Langfuse).

Uso: python -m scripts.latency_report
"""

import json
import statistics

import httpx2

from app.config import get_settings


def vapi_turn_latencies() -> list[float]:
    """Latencia promedio por turno de cada llamada, según Vapi (en ms)."""
    settings = get_settings()
    if settings.vapi_api_key is None:
        raise SystemExit("Falta VAPI_API_KEY en el .env")
    token = settings.vapi_api_key.get_secret_value()
    with httpx2.Client(
        base_url="https://api.vapi.ai",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    ) as http:
        response = http.get(
            "/call", params={"assistantId": settings.vapi_assistant_id, "limit": 50}
        )
    response.raise_for_status()
    calls = response.json()
    values = []
    for call in calls:
        metrics = (call.get("artifact") or {}).get("performanceMetrics") or {}
        if "turnLatencyAverage" in metrics:
            values.append(float(metrics["turnLatencyAverage"]))
    if not values and calls:
        artifact = calls[0].get("artifact") or {}
        print("Vapi no trajo turnLatencyAverage. Campos del artifact:")
        print(json.dumps(sorted(artifact.keys())))
    return values


def langfuse_tool_latencies() -> list[float]:
    """latency_ms de cada span de tool enviado a Langfuse."""
    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        raise SystemExit("Faltan las llaves de Langfuse en el .env")
    auth = (
        settings.langfuse_public_key,
        settings.langfuse_secret_key.get_secret_value(),
    )
    params = {
        "type": "SPAN",
        "fields": "core,basic,metadata",
        "limit": 1000,
        "fromStartTime": "2026-11-07T00:00:00Z",
        "toStartTime": "2026-12-31T00:00:00Z",
    }
    with httpx2.Client(base_url=settings.langfuse_base_url, timeout=30) as http:
        response = http.get("/api/public/v2/observations", params=params, auth=auth)
    response.raise_for_status()
    values = []
    for item in response.json().get("data", []):
        if not str(item.get("name", "")).startswith("tool"):
            continue
        metadata = item.get("metadata") or {}
        latency = metadata.get("latency_ms")
        if latency is None and isinstance(metadata.get("attributes"), dict):
            latency = metadata["attributes"].get("latency_ms")
        if latency is not None:
            values.append(float(latency))
    return values


def summary(name: str, values: list[float]) -> None:
    if not values:
        print(f"{name}: sin datos")
        return
    print(
        f"{name}: {len(values)} muestras · promedio {statistics.mean(values):.0f} ms"
        f" · mediana {statistics.median(values):.0f} ms · máximo {max(values):.0f} ms"
    )


def main() -> None:
    summary("Vapi, latencia por turno", vapi_turn_latencies())
    summary("Langfuse, latencia de tools", langfuse_tool_latencies())


if __name__ == "__main__":
    main()