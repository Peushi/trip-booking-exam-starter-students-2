# Optimistic Locking

## Category

A2 - Concurrency control

## Problem

The flight and hotel services checked inventory availability and decremented it in two separate operations. Under concurrent requests, multiple clients could pass the availability check before any decrement was visible, resulting in negative inventory (e.g. `seats_available: -19` with 20 concurrent requests on a flight with 1 seat).

## Invariant or guarantee

The number of available seats and rooms must never become negative. At most one concurrent request can successfully claim the last available unit.

## Modified files

- `flight_service/main.py`
- `flight_service/db.py`
- `hotel_service/main.py`
- `hotel_service/db.py`

## Behavior before

Two concurrent requests both read `seats_available = 1`, both passed the availability check, and both decremented the inventory. Final result: `seats_available = -1`. With 20 concurrent requests, the result was `seats_available = -19`.

## Behavior after

Each row has a `version` integer. The UPDATE includes `AND version = $3` and increments `version = version + 1`. Only one concurrent request wins; the others find the version has changed and receive a 409 conflict response. Final result: `seats_available = 0`, exactly one booking confirmed.

## How to test

```bash
docker compose run --rm tools pytest tests/test_optimistic_locking.py -v
```

Expected output: 2 passed. One booking succeeds, 19 are rejected with 409.

## Limitation

Rejected requests receive a 409 and must retry manually. The trip service does not currently retry on conflict, so a rejected booking results in a failed trip. The cancellation path is also not protected against concurrent cancellations.