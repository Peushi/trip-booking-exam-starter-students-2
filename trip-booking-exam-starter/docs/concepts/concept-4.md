# Persistent Database Idempotency Key Engine

## Category
Category C

## Problem
In the baseline application, network latency or client-side timeouts cause users to automatically retry their requests. Because the trip-creation route was not idempotent, every network retry caused duplicate database records and spawned redundant downstream mutations across external flight, hotel, and payment services, heavily corrupting the distributed system state.

## Invariant or guarantee
Any request submitted to the `/trips` endpoint accompanied by a unique `X-Idempotency-Key` header will execute its underlying mutation path exactly once. Duplicate retries will instantly receive the identical cached response payload of the initial execution without altering the system state. Concurrent twin requests attempting to race the system will be safely rejected with an HTTP 409 status.

## Modified files
- `trip_service/db.py`
- `trip_service/main.py`
- `scripts/demo_duplicate_request.py`
- `scripts/smoke_success.py`

## Behavior before
When a client re-sent a trip registration due to an assumed network drop, the system processed it as a brand-new entity, double-booking hotel rooms, double-reserving flight seats, and charging the user's payment method multiple times.

## Behavior after
An atomic database row insertion logs a `PENDING` state lock. Concurrent duplicate executions hit a unique index constraint and return an HTTP 409 Conflict. Upon completion, the final response payload is persisted, allowing all future retries to safely read the original output and immediately return a 201 Cache Hit.

## How to test
Rebuild the docker environment and run the refactored automated demonstration script:
`docker compose run --rm tools python scripts/demo_duplicate_request.py`

## Limitation
The idempotency keys are stored permanently inside the PostgreSQL relational database engine. Over long operational periods, this table will accumulate substantial tracking volume, requiring an automated background pruning task or database partitioning scheme to clean out keys older than a standard retry window (e.g., 24 to 48 hours).