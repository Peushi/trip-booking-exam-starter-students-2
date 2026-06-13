from __future__ import annotations

import asyncio
import os

import asyncpg

pool: asyncpg.Pool | None = None


def database_url() -> str:
    return os.getenv("HOTEL_DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/hotel_db")


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
    raise RuntimeError("Could not connect to hotel database") from last_error


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
        CREATE TABLE IF NOT EXISTS hotels (
            id TEXT PRIMARY KEY,
            city TEXT NOT NULL,
            name TEXT NOT NULL,
            rooms_available INTEGER NOT NULL,
            price_per_night_cents INTEGER NOT NULL
        )
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS hotel_reservations (
            id UUID PRIMARY KEY,
            trip_id UUID NOT NULL,
            hotel_id TEXT NOT NULL,
            traveler_name TEXT NOT NULL,
            nights INTEGER NOT NULL,
            rooms INTEGER NOT NULL,
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
        INSERT INTO hotels (id, city, name, rooms_available, price_per_night_cents)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (id) DO NOTHING
        """,
        [
            ("HT-ONE-ROOM", "Tokyo", "Tokyo Central Hotel", 1, 12000),
            ("HT-MANY-ROOMS", "Berlin", "Berlin City Hotel", 10, 9000),
        ],
    )


async def reset_db() -> None:
    db = get_pool()
    await db.execute("DELETE FROM hotel_reservations")
    await db.execute("DELETE FROM hotels")
    await seed_db()


async def state() -> dict[str, list[dict]]:
    db = get_pool()
    hotels = await db.fetch("SELECT * FROM hotels ORDER BY id")
    reservations = await db.fetch("SELECT * FROM hotel_reservations ORDER BY created_at, id")
    return {
        "hotels": [dict(row) for row in hotels],
        "hotel_reservations": [dict(row) for row in reservations],
    }
