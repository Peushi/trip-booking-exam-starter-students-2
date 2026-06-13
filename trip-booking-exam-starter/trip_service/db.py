from __future__ import annotations

import asyncio
import os
from typing import Any
from uuid import UUID, uuid4

import asyncpg

pool: asyncpg.Pool | None = None


def database_url() -> str:
    return os.getenv("TRIP_DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/trip_db")


async def connect_with_retry() -> None:
    global pool
    last_error: Exception | None = None
    for _ in range(40):
        try:
            pool = await asyncpg.create_pool(database_url())
            return
        except Exception as exc:  # pragma: no cover - startup race in Docker
            last_error = exc
            await asyncio.sleep(1)
    raise RuntimeError("Could not connect to trip database") from last_error


def get_pool() -> asyncpg.Pool:
    if pool is None:
        raise RuntimeError("Database pool is not initialized")
    return pool


async def close() -> None:
    if pool is not None:
        await pool.close()


async def init_db() -> None:
    await get_pool().execute(
        """
        CREATE TABLE IF NOT EXISTS trips (
            id UUID PRIMARY KEY,
            user_id TEXT NOT NULL,
            traveler_name TEXT NOT NULL,
            flight_id TEXT NOT NULL,
            hotel_id TEXT NOT NULL,
            nights INTEGER NOT NULL,
            status TEXT NOT NULL,
            flight_booking_id UUID,
            hotel_reservation_id UUID,
            payment_authorization_id UUID,
            amount_cents INTEGER,
            error_message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
   # changes made for CATEGORY-C ( table made to store idempotency keys for each user to avoid duplicate trip creation  )

    await get_pool().execute(
        """
        CREATE TABLE IF NOT EXISTS idempotency_keys (
            user_key TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            saved_code INTEGER,
            saved_body TEXT
        )
        """ 
    )


async def reset_db() -> None:
    await get_pool().execute("DELETE FROM trips")


async def create_trip(
    *,
    user_id: str,
    traveler_name: str,
    flight_id: str,
    hotel_id: str,
    nights: int,
) -> dict:
    trip_id = uuid4()
    row = await get_pool().fetchrow(
        """
        INSERT INTO trips (id, user_id, traveler_name, flight_id, hotel_id, nights, status)
        VALUES ($1, $2, $3, $4, $5, $6, 'PENDING')
        RETURNING *
        """,
        trip_id,
        user_id,
        traveler_name,
        flight_id,
        hotel_id,
        nights,
    )
    return dict(row)


async def update_trip(trip_id: UUID, **fields: Any) -> dict:
    if not fields:
        row = await get_pool().fetchrow("SELECT * FROM trips WHERE id = $1", trip_id)
        return dict(row)

    names = list(fields)
    assignments = [f"{name} = ${index + 2}" for index, name in enumerate(names)]
    assignments.append("updated_at = now()")
    sql = f"UPDATE trips SET {', '.join(assignments)} WHERE id = $1 RETURNING *"
    row = await get_pool().fetchrow(sql, trip_id, *[fields[name] for name in names])
    return dict(row)


async def get_trip(trip_id: UUID) -> dict | None:
    row = await get_pool().fetchrow("SELECT * FROM trips WHERE id = $1", trip_id)
    return dict(row) if row else None


async def state() -> dict[str, list[dict]]:
    rows = await get_pool().fetch("SELECT * FROM trips ORDER BY created_at, id")
    return {"trips": [dict(row) for row in rows]}




#  changes made for CATEFORY-C (asynchronous function to check if the idempotency key already exists in the database for a given user_key)

async def get_idempotency_pending(key: str) ->  None:
    await get_pool().execute("INSERT INTO idempotency_keys (user_key, status) VALUES ($1, 'PENDING') ", key )

async def save_idempotency_complete(key: str, code: int, body: str ) ->  None:
    await get_pool().execute("UPDATE idempotency_keys SET status = 'COMPLETED' , saved_code = $1 , saved_body = $2 WHERE user_key = $3 ", code, body, key )

async def  remove_idempotency(key: str)-> None:
    await get_pool().execute("DELETE FROM idempotency_keys WHERE user_key = $1 ", key )
    