from __future__ import annotations

from uuid import uuid4

from shared.rabbitmq import publish_trip_confirmed


def build_trip_confirmed_event(trip: dict) -> dict:
    return {
        "event_id": str(uuid4()),
        "event_type": "trip.confirmed",
        "version": 1,
        "trip_id": str(trip["id"]),
        "user_id": trip["user_id"],
        "traveler_name": trip["traveler_name"],
        "flight_id": trip["flight_id"],
        "hotel_id": trip["hotel_id"],
        "amount_cents": trip["amount_cents"],
    }


async def publish_confirmation(trip: dict, publish_twice: bool) -> None:
    event = build_trip_confirmed_event(trip)
    await publish_trip_confirmed(event)
    if publish_twice:
        # INTENTIONAL NAIVE DESIGN:
        # Publishing the same event twice produces duplicate side effects because
        # the consumer does not deduplicate by event_id.
        await publish_trip_confirmed(event)

