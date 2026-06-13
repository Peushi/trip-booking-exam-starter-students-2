from pydantic import BaseModel, Field


class SimulationOptions(BaseModel):
    flight_delay_after_check_ms: int = 0
    hotel_delay_after_check_ms: int = 0
    hotel_force_fail: bool = False
    payment_force_decline: bool = False
    payment_force_error: bool = False
    payment_delay_ms: int = 0
    publish_event_twice: bool = False


class CreateTripRequest(BaseModel):
    user_id: str
    traveler_name: str
    flight_id: str
    hotel_id: str
    nights: int
    simulate: SimulationOptions = Field(default_factory=SimulationOptions)

