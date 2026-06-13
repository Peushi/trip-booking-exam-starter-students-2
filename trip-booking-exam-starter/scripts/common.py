from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

import httpx

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from shared.rabbitmq import purge_notification_queue

TRIP_URL = os.getenv("TRIP_URL", "http://localhost:8000")
FLIGHT_URL = os.getenv("FLIGHT_URL", "http://localhost:8001")
HOTEL_URL = os.getenv("HOTEL_URL", "http://localhost:8002")
PAYMENT_URL = os.getenv("PAYMENT_URL", "http://localhost:8003")
NOTIFICATION_URL = os.getenv("NOTIFICATION_URL", "http://localhost:8004")

SERVICES = [
    ("trip-service", TRIP_URL),
    ("flight-service", FLIGHT_URL),
    ("hotel-service", HOTEL_URL),
    ("payment-service", PAYMENT_URL),
    ("notification-api", NOTIFICATION_URL),
]


def pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, default=str)


def reset_all() -> None:
    asyncio.run(purge_notification_queue())
    with httpx.Client(timeout=10) as client:
        for _, base_url in SERVICES:
            client.post(f"{base_url}/admin/reset").raise_for_status()


def get_state() -> dict[str, Any]:
    with httpx.Client(timeout=10) as client:
        return {
            "trip-service": client.get(f"{TRIP_URL}/debug/state").json(),
            "flight-service": client.get(f"{FLIGHT_URL}/debug/state").json(),
            "hotel-service": client.get(f"{HOTEL_URL}/debug/state").json(),
            "payment-service": client.get(f"{PAYMENT_URL}/debug/state").json(),
            "notification-api": client.get(f"{NOTIFICATION_URL}/debug/state").json(),
        }


def wait_for_notifications(trip_id: str, minimum: int = 1, timeout_seconds: float = 5.0) -> list[dict[str, Any]]:
    deadline = time.monotonic() + timeout_seconds
    with httpx.Client(timeout=10) as client:
        while time.monotonic() < deadline:
            notifications = client.get(f"{NOTIFICATION_URL}/notifications/{trip_id}").json()
            if len(notifications) >= minimum:
                return notifications
            time.sleep(0.2)
        return client.get(f"{NOTIFICATION_URL}/notifications/{trip_id}").json()


def create_trip(payload: dict[str, Any]) -> httpx.Response:
    with httpx.Client(timeout=15) as client:
        return client.post(f"{TRIP_URL}/trips", json=payload)


def base_trip_payload(**simulate: Any) -> dict[str, Any]:
    return {
        "user_id": "user-1",
        "traveler_name": "Ada Lovelace",
        "flight_id": "FL-MANY-SEATS",
        "hotel_id": "HT-MANY-ROOMS",
        "nights": 2,
        "simulate": simulate,
    }
