from __future__ import annotations

import asyncio
import os

import asyncpg

pool: asyncpg.Pool | None = None


def database_url() -> str:
    return os.getenv("PAYMENT_DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/payment_db")


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
    raise RuntimeError("Could not connect to payment database") from last_error


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
        CREATE TABLE IF NOT EXISTS payment_authorizations (
            id UUID PRIMARY KEY,
            trip_id UUID NOT NULL,
            amount_cents INTEGER NOT NULL,
            status TEXT NOT NULL,
            failure_reason TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


async def reset_db() -> None:
    await get_pool().execute("DELETE FROM payment_authorizations")


async def state() -> dict[str, list[dict]]:
    rows = await get_pool().fetch("SELECT * FROM payment_authorizations ORDER BY created_at, id")
    return {"payment_authorizations": [dict(row) for row in rows]}
