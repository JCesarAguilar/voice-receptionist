"""El aviso (evento) que Culqi envía a nuestro webhook."""

import json
from typing import Any

from pydantic import BaseModel, ConfigDict


class CulqiEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    data: dict[str, Any] | str

    def order_id(self) -> str | None:
        """El id de la orden, si el evento trae una. Si no, None."""
        data = self.data
        if isinstance(data, str):  # Culqi a veces manda `data` como texto JSON
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return None
        if not isinstance(data, dict) or data.get("object") != "order":
            return None
        order_id = data.get("id")
        return order_id if isinstance(order_id, str) else None
