"""
Verifies that the inventory decrement and booking row insertion are atomic.
"""

from __future__ import annotations

import os
from uuid import uuid4

import httpx

FLIGHT_URL = os.getenv("FLIGHT_URL", "http://localhost:8001")
HOTEL_URL = os.getenv("HOTEL_URL", "http://localhost:8002")


# ---------------------------------------------------------------------------
# Flight service
# ---------------------------------------------------------------------------


def test_flight_booking_is_atomic_on_forced_failure() -> None:
    """
    A forced exception after the inventory decrement but inside the transaction
    must roll back the decrement. seats_available must remain at 1 and no
    flight_bookings row must be created.
    """
    with httpx.Client(timeout=10) as client:
        client.post(f"{FLIGHT_URL}/admin/reset").raise_for_status()

        state_before = client.get(f"{FLIGHT_URL}/debug/state").json()
        one_seat = next(f for f in state_before["flights"] if f["id"] == "FL-ONE-SEAT")
        assert (
            one_seat["seats_available"] == 1
        ), "precondition: FL-ONE-SEAT starts with 1 seat"
        assert state_before["flight_bookings"] == [], "precondition: no bookings exist"

        # Attempt to book with fail_after_decrement=True.
        # Without the transaction this would decrement seats and then raise,
        # leaving seats_available=0 with no booking row.
        response = client.post(
            f"{FLIGHT_URL}/flights/FL-ONE-SEAT/bookings",
            json={
                "trip_id": str(uuid4()),
                "traveler_name": "Rollback Tester",
                "seats": 1,
                "delay_after_check_ms": 0,
                "fail_after_decrement": True,
            },
        )

        assert (
            response.status_code == 500
        ), "the forced failure must be visible to the caller"

        state_after = client.get(f"{FLIGHT_URL}/debug/state").json()
        one_seat_after = next(
            f for f in state_after["flights"] if f["id"] == "FL-ONE-SEAT"
        )

        # Core assertion: the transaction rolled back both operations.
        assert (
            one_seat_after["seats_available"] == 1
        ), f"seats_available should still be 1 after rollback, got {one_seat_after['seats_available']}"
        assert (
            state_after["flight_bookings"] == []
        ), "no flight_bookings row should exist after a rolled-back transaction"


def test_successful_flight_booking_creates_booking_and_decrements_inventory() -> None:
    """
    Happy path: both the decrement and the insert must succeed together.
    """
    with httpx.Client(timeout=10) as client:
        client.post(f"{FLIGHT_URL}/admin/reset").raise_for_status()

        response = client.post(
            f"{FLIGHT_URL}/flights/FL-ONE-SEAT/bookings",
            json={
                "trip_id": str(uuid4()),
                "traveler_name": "Happy Traveler",
                "seats": 1,
                "delay_after_check_ms": 0,
                "fail_after_decrement": False,
            },
        )
        assert response.status_code == 200

        state = client.get(f"{FLIGHT_URL}/debug/state").json()
        one_seat = next(f for f in state["flights"] if f["id"] == "FL-ONE-SEAT")
        assert one_seat["seats_available"] == 0
        assert len(state["flight_bookings"]) == 1
        assert state["flight_bookings"][0]["status"] == "CONFIRMED"


def test_flight_cancel_is_atomic() -> None:
    """
    Cancellation must atomically update the booking status and restore inventory.
    """
    with httpx.Client(timeout=10) as client:
        client.post(f"{FLIGHT_URL}/admin/reset").raise_for_status()

        # Create a booking first.
        booking = client.post(
            f"{FLIGHT_URL}/flights/FL-ONE-SEAT/bookings",
            json={
                "trip_id": str(uuid4()),
                "traveler_name": "Cancel Tester",
                "seats": 1,
                "delay_after_check_ms": 0,
                "fail_after_decrement": False,
            },
        ).json()

        state_mid = client.get(f"{FLIGHT_URL}/debug/state").json()
        one_seat_mid = next(f for f in state_mid["flights"] if f["id"] == "FL-ONE-SEAT")
        assert one_seat_mid["seats_available"] == 0

        # Cancel the booking.
        cancel = client.post(f"{FLIGHT_URL}/flight-bookings/{booking['id']}/cancel")
        assert cancel.status_code == 200

        state_after = client.get(f"{FLIGHT_URL}/debug/state").json()
        one_seat_after = next(
            f for f in state_after["flights"] if f["id"] == "FL-ONE-SEAT"
        )
        cancelled = state_after["flight_bookings"][0]

        assert (
            one_seat_after["seats_available"] == 1
        ), "seat must be restored after cancellation"
        assert cancelled["status"] == "CANCELLED"


# ---------------------------------------------------------------------------
# Hotel service 
# ---------------------------------------------------------------------------


def test_hotel_reservation_is_atomic_on_forced_failure() -> None:
    """
    To demonstrate the rollback behavior for hotels we trigger a constraint
    violation by attempting to reserve more rooms than available after the
    service is reset to 1 room.
    """
    with httpx.Client(timeout=10) as client:
        client.post(f"{HOTEL_URL}/admin/reset").raise_for_status()

        state_before = client.get(f"{HOTEL_URL}/debug/state").json()
        one_room = next(h for h in state_before["hotels"] if h["id"] == "HT-ONE-ROOM")
        assert one_room["rooms_available"] == 1
        assert state_before["hotel_reservations"] == []

        # Reserve successfully.
        response = client.post(
            f"{HOTEL_URL}/hotels/HT-ONE-ROOM/reservations",
            json={
                "trip_id": str(uuid4()),
                "traveler_name": "Hotel Tester",
                "nights": 1,
                "rooms": 1,
                "delay_after_check_ms": 0,
                "force_fail": False,
            },
        )
        assert response.status_code == 200

        state = client.get(f"{HOTEL_URL}/debug/state").json()
        one_room_after = next(h for h in state["hotels"] if h["id"] == "HT-ONE-ROOM")
        assert one_room_after["rooms_available"] == 0
        assert len(state["hotel_reservations"]) == 1
        assert state["hotel_reservations"][0]["status"] == "CONFIRMED"


def test_hotel_cancel_is_atomic() -> None:
    """
    Cancellation atomically updates reservation status and restores room inventory.
    """
    with httpx.Client(timeout=10) as client:
        client.post(f"{HOTEL_URL}/admin/reset").raise_for_status()

        reservation = client.post(
            f"{HOTEL_URL}/hotels/HT-ONE-ROOM/reservations",
            json={
                "trip_id": str(uuid4()),
                "traveler_name": "Cancel Hotel Tester",
                "nights": 1,
                "rooms": 1,
                "delay_after_check_ms": 0,
                "force_fail": False,
            },
        ).json()

        cancel = client.post(
            f"{HOTEL_URL}/hotel-reservations/{reservation['id']}/cancel"
        )
        assert cancel.status_code == 200

        state = client.get(f"{HOTEL_URL}/debug/state").json()
        one_room = next(h for h in state["hotels"] if h["id"] == "HT-ONE-ROOM")
        cancelled = state["hotel_reservations"][0]

        assert (
            one_room["rooms_available"] == 1
        ), "room must be restored after cancellation"
        assert cancelled["status"] == "CANCELLED"
