def calculate_amount_cents(
    *,
    flight_price_cents: int,
    hotel_price_per_night_cents: int,
    nights: int,
    rooms: int = 1,
) -> int:
    return flight_price_cents + hotel_price_per_night_cents * nights * rooms

