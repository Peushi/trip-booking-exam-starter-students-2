from uuid import UUID

from pydantic import BaseModel


class FlightBookingRequest(BaseModel):
    trip_id: UUID
    traveler_name: str
    seats: int
    delay_after_check_ms: int = 0
    fail_after_decrement: bool = False

