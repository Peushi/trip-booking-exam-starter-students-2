from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException

from payment_service import db
from payment_service.schemas import PaymentAuthorizationRequest
from shared.faults import maybe_delay
from shared.logging import configure_logging

SERVICE_NAME = "payment-service"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(SERVICE_NAME)
    await db.connect_with_retry()
    await db.init_db()
    yield
    await db.close()


app = FastAPI(title="Payment Service", lifespan=lifespan)


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


@app.post("/payments/authorizations")
async def authorize_payment(request: PaymentAuthorizationRequest) -> dict:
    await maybe_delay(request.delay_ms)

    if request.force_error:
        raise HTTPException(status_code=500, detail="Forced payment service error")

    # INTENTIONAL NAIVE DESIGN:
    # There is no idempotency key. Retrying the same logical request can create
    # several payment authorizations for the same trip.
    payment_id = uuid4()
    if request.force_decline:
        await db.get_pool().fetchrow(
            """
            INSERT INTO payment_authorizations (id, trip_id, amount_cents, status, failure_reason)
            VALUES ($1, $2, $3, 'DECLINED', 'Forced decline')
            RETURNING *
            """,
            payment_id,
            request.trip_id,
            request.amount_cents,
        )
        raise HTTPException(status_code=402, detail="Payment declined")

    row = await db.get_pool().fetchrow(
        """
        INSERT INTO payment_authorizations (id, trip_id, amount_cents, status)
        VALUES ($1, $2, $3, 'AUTHORIZED')
        RETURNING *
        """,
        payment_id,
        request.trip_id,
        request.amount_cents,
    )
    return dict(row)


@app.post("/payments/{payment_id}/cancel")
async def cancel_payment(payment_id: UUID) -> dict:
    row = await db.get_pool().fetchrow(
        "UPDATE payment_authorizations SET status = 'CANCELLED' WHERE id = $1 RETURNING *",
        payment_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Payment authorization not found")
    return dict(row)
