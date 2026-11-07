"""Lo que envía y recibe la página de pago."""

from pydantic import BaseModel, Field

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class StartPaymentRequest(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=254)


class StartPaymentResponse(BaseModel):
    order_id: str


class ChargeRequest(BaseModel):
    token_id: str = Field(min_length=1, max_length=100)
    email: str = Field(pattern=EMAIL_PATTERN, max_length=254)


class ChargeResponse(BaseModel):
    paid: bool
