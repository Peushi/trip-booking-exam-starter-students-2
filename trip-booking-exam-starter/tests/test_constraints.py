"""
These tests bypass the application layer and execute SQL directly against
the databases to verify that PostgreSQL rejects constraint-violating writes.
"""

from __future__ import annotations

import asyncio
import os

import asyncpg
import pytest

FLIGHT_DB_URL = os.getenv(
    "FLIGHT_DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/flight_db"
)
HOTEL_DB_URL = os.getenv(
    "HOTEL_DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/hotel_db"
)


async def flight_conn() -> asyncpg.Connection:
    return await asyncpg.connect(FLIGHT_DB_URL)


async def hotel_conn() -> asyncpg.Connection:
    return await asyncpg.connect(HOTEL_DB_URL)

# ---------------------------------------------------------------------------
# flight
# ---------------------------------------------------------------------------


def test_flights_seats_available_cannot_go_negative() -> None:
    """
    Directly setting seats_available to -1 must be rejected by the CHECK constraint.
    """

    async def run():
        conn = await flight_conn()
        try:
            with pytest.raises(asyncpg.exceptions.CheckViolationError):
                await conn.execute(
                    "UPDATE flights SET seats_available = -1 WHERE id = 'FL-ONE-SEAT'"
                )
        finally:
            await conn.close()

    asyncio.run(run())


def test_flights_price_cents_must_be_positive() -> None:
    """
    Setting price_cents to 0 must be rejected.
    """

    async def run():
        conn = await flight_conn()
        try:
            with pytest.raises(asyncpg.exceptions.CheckViolationError):
                await conn.execute(
                    "UPDATE flights SET price_cents = 0 WHERE id = 'FL-ONE-SEAT'"
                )
        finally:
            await conn.close()

    asyncio.run(run())


def test_flight_bookings_seats_must_be_positive() -> None:
    """
    Inserting a flight booking with seats = 0 must be rejected.
    """

    async def run():
        conn = await flight_conn()
        try:
            with pytest.raises(asyncpg.exceptions.CheckViolationError):
                await conn.execute("""
                    INSERT INTO flight_bookings (id, trip_id, flight_id, traveler_name, seats, status)
                    VALUES (gen_random_uuid(), gen_random_uuid(), 'FL-ONE-SEAT', 'Test', 0, 'CONFIRMED')
                    """)
        finally:
            await conn.close()

    asyncio.run(run())


# ---------------------------------------------------------------------------
# hotel
# ---------------------------------------------------------------------------


def test_hotels_rooms_available_cannot_go_negative() -> None:
    """
    Directly setting rooms_available to -1 must be rejected by the CHECK constraint.
    """

    async def run():
        conn = await hotel_conn()
        try:
            with pytest.raises(asyncpg.exceptions.CheckViolationError):
                await conn.execute(
                    "UPDATE hotels SET rooms_available = -1 WHERE id = 'HT-ONE-ROOM'"
                )
        finally:
            await conn.close()

    asyncio.run(run())


def test_hotels_price_per_night_must_be_positive() -> None:
    """
    Setting price_per_night_cents to 0 must be rejected.
    """

    async def run():
        conn = await hotel_conn()
        try:
            with pytest.raises(asyncpg.exceptions.CheckViolationError):
                await conn.execute(
                    "UPDATE hotels SET price_per_night_cents = 0 WHERE id = 'HT-ONE-ROOM'"
                )
        finally:
            await conn.close()

    asyncio.run(run())


def test_hotel_reservations_nights_must_be_positive() -> None:
    """
    Inserting a reservation with nights = 0 must be rejected.
    """

    async def run():
        conn = await hotel_conn()
        try:
            with pytest.raises(asyncpg.exceptions.CheckViolationError):
                await conn.execute("""
                    INSERT INTO hotel_reservations (id, trip_id, hotel_id, traveler_name, nights, rooms, status)
                    VALUES (gen_random_uuid(), gen_random_uuid(), 'HT-ONE-ROOM', 'Test', 0, 1, 'CONFIRMED')
                    """)
        finally:
            await conn.close()

    asyncio.run(run())


def test_hotel_reservations_rooms_must_be_positive() -> None:
    """
    Inserting a reservation with rooms = 0 must be rejected.
    """

    async def run():
        conn = await hotel_conn()
        try:
            with pytest.raises(asyncpg.exceptions.CheckViolationError):
                await conn.execute("""
                    INSERT INTO hotel_reservations (id, trip_id, hotel_id, traveler_name, nights, rooms, status)
                    VALUES (gen_random_uuid(), gen_random_uuid(), 'HT-ONE-ROOM', 'Test', 1, 0, 'CONFIRMED')
                    """)
        finally:
            await conn.close()

    asyncio.run(run())
