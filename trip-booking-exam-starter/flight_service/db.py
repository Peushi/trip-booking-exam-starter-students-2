from __future__ import annotations

import asyncio
import os

import asyncpg

pool: asyncpg.Pool | None = None


def database_url() -> str:
    return os.getenv("FLIGHT_DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/flight_db")


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
    raise RuntimeError("Could not connect to flight database") from last_error


def get_pool() -> asyncpg.Pool:
    if pool is None:
        raise RuntimeError("Database pool is not initialized")
    return pool


async def close() -> None:
    if pool is not None:
        await pool.close()


async def init_db() -> None:
    db = get_pool()
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS flights (
            id TEXT PRIMARY KEY,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            departure_date TEXT NOT NULL,
            seats_available INTEGER NOT NULL,
            price_cents INTEGER NOT NULL
        )
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS flight_bookings (
            id UUID PRIMARY KEY,
            trip_id UUID NOT NULL,
            flight_id TEXT NOT NULL,
            traveler_name TEXT NOT NULL,
            seats INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    await seed_db()


async def seed_db() -> None:
    db = get_pool()
    await db.executemany(
        """
        INSERT INTO flights (id, origin, destination, departure_date, seats_available, price_cents)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (id) DO NOTHING
        """,
        [
            ("FL-ONE-SEAT", "Paris", "Tokyo", "2026-07-01", 1, 80000),
            ("FL-MANY-SEATS", "Paris", "Berlin", "2026-07-02", 10, 15000),
        ],
    )


async def reset_db() -> None:
    db = get_pool()
    await db.execute("DELETE FROM flight_bookings")
    await db.execute("DELETE FROM flights")
    await seed_db()


async def state() -> dict[str, list[dict]]:
    db = get_pool()
    flights = await db.fetch("SELECT * FROM flights ORDER BY id")
    bookings = await db.fetch("SELECT * FROM flight_bookings ORDER BY created_at, id")
    return {
        "flights": [dict(row) for row in flights],
        "flight_bookings": [dict(row) for row in bookings],
    }
