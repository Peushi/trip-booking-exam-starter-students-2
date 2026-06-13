from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI

from notification_api import db
from shared.logging import configure_logging

SERVICE_NAME = "notification-api"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(SERVICE_NAME)
    await db.connect_with_retry()
    await db.init_db()
    yield
    await db.close()


app = FastAPI(title="Notification API", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME}


@app.post("/admin/reset")
async def reset() -> dict[str, str]:
    await db.reset_db()
    return {"status": "ok"}


@app.get("/debug/state")
async def debug_state() -> dict:
    return await db.state()


@app.get("/notifications")
async def notifications() -> list[dict]:
    return (await db.state())["notifications"]


@app.get("/notifications/{trip_id}")
async def notifications_for_trip(trip_id: UUID) -> list[dict]:
    rows = await db.get_pool().fetch(
        "SELECT * FROM notifications WHERE trip_id = $1 ORDER BY created_at, id",
        trip_id,
    )
    return [db.notification_to_dict(row) for row in rows]
