from __future__ import annotations

import os
from typing import Any

import httpx

TIMEOUT_SECONDS = 5.0


def flight_service_url() -> str:
    return os.getenv("FLIGHT_SERVICE_URL", "http://localhost:8001")


def hotel_service_url() -> str:
    return os.getenv("HOTEL_SERVICE_URL", "http://localhost:8002")


def payment_service_url() -> str:
    return os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8003")


async def _request(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        response = await client.request(method, url, json=payload)
    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise RuntimeError(f"{method} {url} failed with {response.status_code}: {detail}")
    return response.json()


async def get_flight(flight_id: str) -> dict[str, Any]:
    return await _request("GET", f"{flight_service_url()}/flights/{flight_id}")


async def book_flight(
    *,
    flight_id: str,
    trip_id: str,
    traveler_name: str,
    delay_after_check_ms: int,
) -> dict[str, Any]:
    return await _request(
        "POST",
        f"{flight_service_url()}/flights/{flight_id}/bookings",
        {
            "trip_id": trip_id,
            "traveler_name": traveler_name,
            "seats": 1,
            "delay_after_check_ms": delay_after_check_ms,
            "fail_after_decrement": False,
        },
    )


async def get_hotel(hotel_id: str) -> dict[str, Any]:
    return await _request("GET", f"{hotel_service_url()}/hotels/{hotel_id}")


async def reserve_hotel(
    *,
    hotel_id: str,
    trip_id: str,
    traveler_name: str,
    nights: int,
    delay_after_check_ms: int,
    force_fail: bool,
) -> dict[str, Any]:
    return await _request(
        "POST",
        f"{hotel_service_url()}/hotels/{hotel_id}/reservations",
        {
            "trip_id": trip_id,
            "traveler_name": traveler_name,
            "nights": nights,
            "rooms": 1,
            "delay_after_check_ms": delay_after_check_ms,
            "force_fail": force_fail,
        },
    )


async def authorize_payment(
    *,
    trip_id: str,
    amount_cents: int,
    force_decline: bool,
    force_error: bool,
    delay_ms: int,
) -> dict[str, Any]:
    return await _request(
        "POST",
        f"{payment_service_url()}/payments/authorizations",
        {
            "trip_id": trip_id,
            "amount_cents": amount_cents,
            "force_decline": force_decline,
            "force_error": force_error,
            "delay_ms": delay_ms,
        },
    )

