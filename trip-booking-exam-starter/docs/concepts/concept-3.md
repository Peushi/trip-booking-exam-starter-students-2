# Durable saga state machine with compensation

## Category

B - Distributed workflow or messaging.

## Problem

In the baseline application, `trip-service` execited the trip booking workflow as a plain sequence of remote calls.

If payment failed after the flight booking and hotel reservation had already succeeded, the trip was marked as `FAILED`, but the flight and hotel resources remained confirmed. This left the system in a partially completed distributed state.

## Invariant or guarantee

A trip should not remain in a half-completed state after a later remote step fails.

if the workflow cannot be completed, the trop enters compensation and previously completed remote steps get cancelled. The final trip state becomes `CANCELLED` if compensation succeeds, or `COMPENSATION_FAILED` if compensation itself fails.

Completed remote step IDs are stored durably in the trip row before moving to the next step.

## Modified files

- `trip_service/main.py`
- `trip_service/clients.py`
- `flight_service/main.py`
- `hotel_service/main.py`
- `payment_service/main.py`
- `tests/test_intentional_flaws.py`
- `scripts/demo_partial_failure.py`

## Behavior before

When payment declined after flight and hotel succeeded:

- the trip was marked as `FAILED`
- the flight booking stayed `CONFIRMED`
- the hotel reservation stayed `CONFIRMED`
- the flight seat and hotel room remained consumed
- the final distributed state was inconsistent

## Behavior after

When payment declines after flight and hotel succeed:

- the trip enters `COMPENSATING`
- the hotel reservation is cancelled
- the flight booking is cancelled
- the hotel room is restored
- the flight seat is restored
- the trip ends as `CANCELLED`
- no confirmation notification is published

Compensation endpoints are idempotent, so retrying cancellation does not restore seats or rooms twice.

## How to test

Run:

```bash
docker compose up --build -d
docker compose run --rm tools python scripts/demo_partial_failure.py
docker compose run --rm tools pytest
```

## The specific automated test is:

```bash
docker compose run --rm tools pytest tests/test_intentional_flaws.py::test_payment_failure_is_compensated_by_saga -v
```

# Limitation

This implementation compensates failures during the booking/payment phase.
It does not yet implement full TCC Try/Confirm/Cancel semantics.
It also does not recover from every possible crash point. For example, if trip-service crashes after a remote step succeeds but before the next local state update is written, manual reconciliation or an additional recovery worker would still be needed.
