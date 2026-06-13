from __future__ import annotations

import asyncio
import json
import os
from typing import Any
from uuid import UUID, uuid4

import asyncpg

pool: asyncpg.Pool | None = None


def database_url() -> str:
    return os.getenv("NOTIFICATION_DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/notification_db")


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
    raise RuntimeError("Could not connect to notification database") from last_error


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
        CREATE TABLE IF NOT EXISTS notifications (
            id UUID PRIMARY KEY,
            event_id UUID NOT NULL,
            trip_id UUID NOT NULL,
            user_id TEXT NOT NULL,
            notification_type TEXT NOT NULL,
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


async def reset_db() -> None:
    await get_pool().execute("DELETE FROM notifications")


async def insert_notification(
    *,
    event_id: UUID,
    trip_id: UUID,
    user_id: str,
    notification_type: str,
    payload: dict[str, Any],
) -> dict:
    # INTENTIONAL NAIVE DESIGN:
    # event_id is not unique. Duplicate events create duplicate notification rows.
    row = await get_pool().fetchrow(
        """
        INSERT INTO notifications (id, event_id, trip_id, user_id, notification_type, payload)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb)
        RETURNING *
        """,
        uuid4(),
        event_id,
        trip_id,
        user_id,
        notification_type,
        json.dumps(payload),
    )
    return notification_to_dict(row)


async def state() -> dict[str, list[dict]]:
    rows = await get_pool().fetch("SELECT * FROM notifications ORDER BY created_at, id")
    return {"notifications": [notification_to_dict(row) for row in rows]}


def notification_to_dict(row: asyncpg.Record) -> dict:
    data = dict(row)
    if isinstance(data.get("payload"), str):
        data["payload"] = json.loads(data["payload"])
    return data
