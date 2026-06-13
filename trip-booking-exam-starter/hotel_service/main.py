from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException

from hotel_service import db
from hotel_service.schemas import HotelReservationRequest
from shared.faults import maybe_delay
from shared.logging import configure_logging

SERVICE_NAME = "hotel-service"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(SERVICE_NAME)
    await db.connect_with_retry()
    await db.init_db()
    yield
    await db.close()


app = FastAPI(title="Hotel Service", lifespan=lifespan)


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


@app.get("/hotels")
async def list_hotels() -> list[dict]:
    rows = await db.get_pool().fetch("SELECT * FROM hotels ORDER BY id")
    return [dict(row) for row in rows]


@app.get("/hotels/{hotel_id}")
async def get_hotel(hotel_id: str) -> dict:
    row = await db.get_pool().fetchrow("SELECT * FROM hotels WHERE id = $1", hotel_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return dict(row)


@app.post("/hotels/{hotel_id}/reservations")
async def reserve_hotel(hotel_id: str, request: HotelReservationRequest) -> dict:
    if request.force_fail:
        raise HTTPException(status_code=500, detail="Forced hotel failure")

    pool = db.get_pool()
    hotel = await pool.fetchrow("SELECT * FROM hotels WHERE id = $1", hotel_id)
    if hotel is None:
        raise HTTPException(status_code=404, detail="Hotel not found")

    # INTENTIONAL NAIVE DESIGN:
    # This check/update is not protected by a transaction or row lock.
    # Several concurrent requests can pass this check before any decrement is visible.
    if hotel["rooms_available"] < request.rooms:
        raise HTTPException(status_code=409, detail="Not enough rooms available")

    await maybe_delay(request.delay_after_check_ms)

    await pool.execute(
        "UPDATE hotels SET rooms_available = rooms_available - $1 WHERE id = $2",
        request.rooms,
        hotel_id,
    )
    reservation_id = uuid4()
    reservation = await pool.fetchrow(
        """
        INSERT INTO hotel_reservations (id, trip_id, hotel_id, traveler_name, nights, rooms, status)
        VALUES ($1, $2, $3, $4, $5, $6, 'CONFIRMED')
        RETURNING *
        """,
        reservation_id,
        request.trip_id,
        hotel_id,
        request.traveler_name,
        request.nights,
        request.rooms,
    )
    return dict(reservation)


@app.post("/hotel-reservations/{reservation_id}/cancel")
async def cancel_reservation(reservation_id: UUID) -> dict:
    pool = db.get_pool()
    reservation = await pool.fetchrow("SELECT * FROM hotel_reservations WHERE id = $1", reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Hotel reservation not found")

    # INTENTIONAL NAIVE DESIGN:
    # Cancellation is not idempotent; calling this twice increments rooms twice.
    updated = await pool.fetchrow(
        "UPDATE hotel_reservations SET status = 'CANCELLED' WHERE id = $1 RETURNING *",
        reservation_id,
    )
    await pool.execute(
        "UPDATE hotels SET rooms_available = rooms_available + $1 WHERE id = $2",
        reservation["rooms"],
        reservation["hotel_id"],
    )
    return dict(updated)

