from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException

from flight_service import db
from flight_service.schemas import FlightBookingRequest
from shared.faults import maybe_delay
from shared.logging import configure_logging

SERVICE_NAME = "flight-service"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(SERVICE_NAME)
    await db.connect_with_retry()
    await db.init_db()
    yield
    await db.close()


app = FastAPI(title="Flight Service", lifespan=lifespan)


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


@app.get("/flights")
async def list_flights() -> list[dict]:
    rows = await db.get_pool().fetch("SELECT * FROM flights ORDER BY id")
    return [dict(row) for row in rows]


@app.get("/flights/{flight_id}")
async def get_flight(flight_id: str) -> dict:
    row = await db.get_pool().fetchrow("SELECT * FROM flights WHERE id = $1", flight_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Flight not found")
    return dict(row)


@app.post("/flights/{flight_id}/bookings")
async def book_flight(flight_id: str, request: FlightBookingRequest) -> dict:
    pool = db.get_pool()
    flight = await pool.fetchrow("SELECT * FROM flights WHERE id = $1", flight_id)
    if flight is None:
        raise HTTPException(status_code=404, detail="Flight not found")

    # INTENTIONAL NAIVE DESIGN:
    # This check/update is not protected by a transaction or row lock.
    # Several concurrent requests can pass this check before any decrement is visible.
    if flight["seats_available"] < request.seats:
        raise HTTPException(status_code=409, detail="Not enough seats available")

    await maybe_delay(request.delay_after_check_ms)

    await pool.execute(
        "UPDATE flights SET seats_available = seats_available - $1 WHERE id = $2",
        request.seats,
        flight_id,
    )

    if request.fail_after_decrement:
        raise HTTPException(status_code=500, detail="Forced failure after decrement")

    booking_id = uuid4()
    booking = await pool.fetchrow(
        """
        INSERT INTO flight_bookings (id, trip_id, flight_id, traveler_name, seats, status)
        VALUES ($1, $2, $3, $4, $5, 'CONFIRMED')
        RETURNING *
        """,
        booking_id,
        request.trip_id,
        flight_id,
        request.traveler_name,
        request.seats,
    )
    return dict(booking)


@app.post("/flight-bookings/{booking_id}/cancel")
async def cancel_booking(booking_id: UUID) -> dict:
    pool = db.get_pool()
    booking = await pool.fetchrow("SELECT * FROM flight_bookings WHERE id = $1", booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Flight booking not found")

    # INTENTIONAL NAIVE DESIGN:
    # Cancellation is not idempotent; calling this twice increments seats twice.
    updated = await pool.fetchrow(
        "UPDATE flight_bookings SET status = 'CANCELLED' WHERE id = $1 RETURNING *",
        booking_id,
    )
    await pool.execute(
        "UPDATE flights SET seats_available = seats_available + $1 WHERE id = $2",
        booking["seats"],
        booking["flight_id"],
    )
    return dict(updated)

