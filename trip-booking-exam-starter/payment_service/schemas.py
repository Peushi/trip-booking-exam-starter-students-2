from uuid import UUID

from pydantic import BaseModel


class PaymentAuthorizationRequest(BaseModel):
    trip_id: UUID
    amount_cents: int
    force_decline: bool = False
    force_error: bool = False
    delay_ms: int = 0

