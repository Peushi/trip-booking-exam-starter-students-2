from uuid import UUID

from pydantic import BaseModel


class HotelReservationRequest(BaseModel):
    trip_id: UUID
    traveler_name: str
    nights: int
    rooms: int
    delay_after_check_ms: int = 0
    force_fail: bool = False

