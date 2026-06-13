from __future__ import annotations

import asyncio
import os
import time

import httpx

from shared.rabbitmq import purge_notification_queue

TRIP_URL = os.getenv("TRIP_URL", "http://localhost:8000")
FLIGHT_URL = os.getenv("FLIGHT_URL", "http://localhost:8001")
HOTEL_URL = os.getenv("HOTEL_URL", "http://localhost:8002")
PAYMENT_URL = os.getenv("PAYMENT_URL", "http://localhost:8003")
NOTIFICATION_URL = os.getenv("NOTIFICATION_URL", "http://localhost:8004")
SERVICE_URLS = [TRIP_URL, FLIGHT_URL, HOTEL_URL, PAYMENT_URL, NOTIFICATION_URL]


def reset_all() -> None:
    asyncio.run(purge_notification_queue())
    with httpx.Client(timeout=10) as client:
        for base_url in SERVICE_URLS:
            client.post(f"{base_url}/admin/reset").raise_for_status()


def trip_payload(**simulate):
    return {
        "user_id": "user-1",
        "traveler_name": "Ada Lovelace",
        "flight_id": "FL-MANY-SEATS",
        "hotel_id": "HT-MANY-ROOMS",
        "nights": 2,
        "simulate": simulate,
    }


def wait_for_notifications(trip_id: str, minimum: int) -> list[dict]:
    deadline = time.monotonic() + 8
    with httpx.Client(timeout=10) as client:
        while time.monotonic() < deadline:
            rows = client.get(f"{NOTIFICATION_URL}/notifications/{trip_id}").json()
            if len(rows) >= minimum:
                return rows
            time.sleep(0.2)
        return client.get(f"{NOTIFICATION_URL}/notifications/{trip_id}").json()


def test_duplicate_request_is_not_idempotent_in_baseline() -> None:
    reset_all()
    payload = trip_payload()
    with httpx.Client(timeout=15) as client:
        first = client.post(f"{TRIP_URL}/trips", json=payload)
        second = client.post(f"{TRIP_URL}/trips", json=payload)
        trips = client.get(f"{TRIP_URL}/trips").json()
        flight_state = client.get(f"{FLIGHT_URL}/debug/state").json()
        hotel_state = client.get(f"{HOTEL_URL}/debug/state").json()
        payment_state = client.get(f"{PAYMENT_URL}/debug/state").json()

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] != second.json()["id"]
    assert len(trips) == 2
    assert len(flight_state["flight_bookings"]) == 2
    assert len(hotel_state["hotel_reservations"]) == 2
    assert len(payment_state["payment_authorizations"]) == 2


def test_payment_failure_leaves_reserved_resources_in_baseline() -> None:
    reset_all()
    with httpx.Client(timeout=15) as client:
        response = client.post(f"{TRIP_URL}/trips", json=trip_payload(payment_force_decline=True))
        trips = client.get(f"{TRIP_URL}/trips").json()
        flight_state = client.get(f"{FLIGHT_URL}/debug/state").json()
        hotel_state = client.get(f"{HOTEL_URL}/debug/state").json()
        payment_state = client.get(f"{PAYMENT_URL}/debug/state").json()

    assert response.status_code == 502
    assert trips[0]["status"] == "FAILED"
    assert flight_state["flight_bookings"][0]["status"] == "CONFIRMED"
    assert hotel_state["hotel_reservations"][0]["status"] == "CONFIRMED"
    assert payment_state["payment_authorizations"][0]["status"] == "DECLINED"


def test_duplicate_event_creates_duplicate_notifications_in_baseline() -> None:
    reset_all()
    with httpx.Client(timeout=15) as client:
        response = client.post(f"{TRIP_URL}/trips", json=trip_payload(publish_event_twice=True))

    assert response.status_code == 200
    notifications = wait_for_notifications(response.json()["id"], minimum=2)
    assert len(notifications) == 2
    assert notifications[0]["event_id"] == notifications[1]["event_id"]
