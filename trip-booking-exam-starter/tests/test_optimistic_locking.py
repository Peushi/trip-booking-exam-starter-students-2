import asyncio
import os
import httpx
import pytest

FLIGHT_URL = os.getenv("FLIGHT_URL", "http://flight-service:8001")
HOTEL_URL = os.getenv("HOTEL_URL", "http://hotel-service:8002")


@pytest.mark.asyncio
async def test_flight_optimistic_locking_prevents_overbooking():
    """20 concurrent requests on a 1-seat flight: exactly 1 should succeed."""
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{FLIGHT_URL}/admin/reset")

        async def book():
            return await client.post(
                f"{FLIGHT_URL}/flights/FL-ONE-SEAT/bookings",
                json={
                    "trip_id": "00000000-0000-0000-0000-000000000001",
                    "traveler_name": "Test User",
                    "seats": 1,
                    "delay_after_check_ms": 0,
                    "fail_after_decrement": False,
                },
            )

        results = await asyncio.gather(*[book() for _ in range(20)])
        statuses = [r.status_code for r in results]

        assert statuses.count(200) == 1, f"Expected 1 success, got {statuses.count(200)}"
        assert statuses.count(409) == 19, f"Expected 19 conflicts, got {statuses.count(409)}"

        state = await client.get(f"{FLIGHT_URL}/debug/state")
        seats = next(f["seats_available"] for f in state.json()["flights"] if f["id"] == "FL-ONE-SEAT")
        assert seats == 0
        assert seats >= 0, "seats_available must never go negative"


@pytest.mark.asyncio
async def test_hotel_optimistic_locking_prevents_overbooking():
    """20 concurrent requests on a 1-room hotel: exactly 1 should succeed."""
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{HOTEL_URL}/admin/reset")

        async def reserve():
            return await client.post(
                f"{HOTEL_URL}/hotels/HT-ONE-ROOM/reservations",
                json={
                    "trip_id": "00000000-0000-0000-0000-000000000002",
                    "traveler_name": "Test User",
                    "rooms": 1,
                    "nights": 1,
                    "delay_after_check_ms": 0,
                    "fail_after_decrement": False,
                    "force_fail": False,
                },
            )

        results = await asyncio.gather(*[reserve() for _ in range(20)])
        statuses = [r.status_code for r in results]

        assert statuses.count(200) == 1, f"Expected 1 success, got {statuses.count(200)}"
        assert statuses.count(409) == 19, f"Expected 19 conflicts, got {statuses.count(409)}"

        state = await client.get(f"{HOTEL_URL}/debug/state")
        rooms = next(h["rooms_available"] for h in state.json()["hotels"] if h["id"] == "HT-ONE-ROOM")
        assert rooms == 0
        assert rooms >= 0, "rooms_available must never go negative"