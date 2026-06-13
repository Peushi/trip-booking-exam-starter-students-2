from __future__ import annotations

import asyncio
from uuid import uuid4

import httpx

from common import FLIGHT_URL, pretty, reset_all


async def try_book(client: httpx.AsyncClient) -> httpx.Response:
    return await client.post(
        f"{FLIGHT_URL}/flights/FL-ONE-SEAT/bookings",
        json={
            "trip_id": str(uuid4()),
            "traveler_name": "Race Condition Student",
            "seats": 1,
            "delay_after_check_ms": 200,
            "fail_after_decrement": False,
        },
    )


async def run_race() -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        responses = await asyncio.gather(*[try_book(client) for _ in range(20)])
        state = (await client.get(f"{FLIGHT_URL}/debug/state")).json()

    successful = [response for response in responses if response.status_code == 200]
    rejected = [response for response in responses if response.status_code == 409]
    one_seat = next(flight for flight in state["flights"] if flight["id"] == "FL-ONE-SEAT")

    print(f"Successful bookings: {len(successful)}")
    print(f"Rejected bookings: {len(rejected)}")
    print(f"Final seats_available: {one_seat['seats_available']}")
    print("This demonstrates a race condition.")
    print("Final flight state:")
    print(pretty(state))


def main() -> None:
    reset_all()
    asyncio.run(run_race())


if __name__ == "__main__":
    main()

