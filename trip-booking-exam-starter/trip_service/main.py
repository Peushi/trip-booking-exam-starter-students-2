from __future__ import annotations

# CHANGES MADE FOR CATEGORY-C: Imported built-in JSON to serialize models safely
import json

###

import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, Header, Depends, Response, HTTPException, status

from shared.logging import configure_logging
from trip_service import clients, db, events
from trip_service.pricing import calculate_amount_cents
from trip_service.schemas import CreateTripRequest

SERVICE_NAME = "trip-service"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(SERVICE_NAME)
    await db.connect_with_retry()
    await db.init_db()
    yield
    await db.close()


app = FastAPI(title="Trip Service", lifespan=lifespan)


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


@app.get("/trips")
async def list_trips() -> list[dict]:
    return (await db.state())["trips"]


@app.get("/trips/{trip_id}")
async def get_trip(trip_id: UUID) -> dict:
    trip = await db.get_trip(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


# changes made for CATEGORY-C(idempotency)

# COMPENSATION HELPER FOR THE SAGA
async def compensate_trip(trip_id: UUID, original_error: Exception) -> dict:
    trip = await db.update_trip(
        trip_id,
        status="COMPENSATING",
        error_message=str(original_error),
    )

    compensation_errors: list[str] = []

    if trip.get("payment_authorization_id") is not None:
        try:
            await clients.cancel_payment(payment_id=str(trip["payment_authorization_id"]))
        except Exception as exc:
            logging.exception("Payment compensation failed")
            compensation_errors.append(f"payment compensation failed: {exc}")

    if trip.get("hotel_reservation_id") is not None:
        try:
            await clients.cancel_hotel_reservation(reservation_id=str(trip["hotel_reservation_id"]))
        except Exception as exc:
            logging.exception("Hotel compensation failed")
            compensation_errors.append(f"hotel compensation failed: {exc}")

    if trip.get("flight_booking_id") is not None:
        try:
            await clients.cancel_flight_booking(booking_id=str(trip["flight_booking_id"]))
        except Exception as exc:
            logging.exception("Flight compensation failed")
            compensation_errors.append(f"flight compensation failed: {exc}")
    
    if compensation_errors:
        return await db.update_trip(
            trip_id,
            status="COMPENSATION_FAILED",
            error_message=str(original_error) + " | " + " | ".join(compensation_errors),
        )
    
    return await db.update_trip(
        trip_id,
        status="CANCELLED",
        error_message=str(original_error)
    )


# after each successful remote call, the trip row is updated durably
# FLIGHT_BOOKED + flight_booking_id
# HOTEL_RESERVED + hotel_reservation_id
# PAYMENT_AUTHORIZED + payment_authorization_id

@app.post("/trips")
async def create_trip(
    request: CreateTripRequest,
    response: Response,
    x_idempotency_key: str = Header(None),
) -> dict:

    #Reject client request instantly if header key is missing
    if not x_idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Bad Request: Missing required 'X-Idempotency-Key' header.",
        )

    #to check if this operation happened before
    existing = await db.get_idempotency(x_idempotency_key)

    if existing is not None:
        if existing["status"] == "PENDING":
            raise HTTPException(
                status_code=409,
                detail="Request is already being processed. Please wait for the result.",
            )

        # If it is COMPLETED execute and return cached output
        if existing["status"] == "COMPLETED":
            response.status_code = existing["saved_code"]
            return json.loads(existing["saved_body"])

    #Register key status as PENDING in tracking table
    try:
        await db.save_idempotency_pending(x_idempotency_key)
    except Exception:
        raise HTTPException(
            status_code=409,
            detail="Concurrent request collision. Please retry shortly.",
        )

    # execute the service logic
    try:
        trip = await db.create_trip(
            user_id=request.user_id,
            traveler_name=request.traveler_name,
            flight_id=request.flight_id,
            hotel_id=request.hotel_id,
            nights=request.nights,
        )
        trip_id = trip["id"]

        flight_booking = await clients.book_flight(
            flight_id=request.flight_id,
            trip_id=str(trip_id),
            traveler_name=request.traveler_name,
            delay_after_check_ms=request.simulate.flight_delay_after_check_ms,
        )
        trip = await db.update_trip(
            trip_id, 
            flight_booking_id=UUID(flight_booking["id"]),
            status="FLIGHT_BOOKED",
            error_message=None,
        )

        hotel_reservation = await clients.reserve_hotel(
            hotel_id=request.hotel_id,
            trip_id=str(trip_id),
            traveler_name=request.traveler_name,
            nights=request.nights,
            delay_after_check_ms=request.simulate.hotel_delay_after_check_ms,
            force_fail=request.simulate.hotel_force_fail,
        )
        trip = await db.update_trip(
            trip_id, 
            hotel_reservation_id=UUID(hotel_reservation["id"]),
            status="HOTEL_RESERVED",
            error_message=None,
        )

        # Safely retrieve service inventory configurations and evaluate pricing rules
        flight = await clients.get_flight(request.flight_id)
        hotel = await clients.get_hotel(request.hotel_id)
        amount_cents = calculate_amount_cents(
            flight_price_cents=flight["price_cents"],
            hotel_price_per_night_cents=hotel["price_per_night_cents"],
            nights=request.nights,
        )
        trip = await db.update_trip(
            trip_id, 
            amount_cents=amount_cents,
            error_message=None,
        )

        payment = await clients.authorize_payment(
            trip_id=str(trip_id),
            amount_cents=amount_cents,
            force_decline=request.simulate.payment_force_decline,
            force_error=request.simulate.payment_force_error,
            delay_ms=request.simulate.payment_delay_ms,
        )
        trip = await db.update_trip(
            trip_id,
            payment_authorization_id=UUID(payment["id"]),
            status="PAYMENT_AUTHORIZED",
            error_message=None,
        )

        trip = await db.update_trip(
            trip_id,
            status="CONFIRMED",
            error_message=None,
        )

        # commit response to cache to avoid duplicate future side effects
        stringified_trip = json.dumps(trip, default=str)
        await db.save_idempotency_complete(x_idempotency_key, 201, stringified_trip)

    except Exception as exc:
        # RECOVERY CLEANUP: Drop request token if internal steps crash so client can retry safely
        await db.remove_idempotency(x_idempotency_key)
        
        # SAGA COMPENSATION
        compensated = await compensate_trip(trip_id, exc)
        raise HTTPException(
            status_code=502, 
            detail={
                "trip_id": str(trip_id), 
                "status": compensated["status"],
                "error": compensated["error_message"],
            },
        )

    try:
        await events.publish_confirmation(
            trip, publish_twice=request.simulate.publish_event_twice
        )
    except Exception:
        logging.exception("Failed to publish trip.confirmed event")

    return trip