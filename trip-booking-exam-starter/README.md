# Trip Booking Exam Starter

This repository contains a runnable, intentionally naive distributed trip-booking application for a Distributed Systems final exam.

This application is intentionally naive.
It is not production-ready.
Several correctness mechanisms are missing on purpose.
Your exam work will consist in selecting some of these weaknesses and implementing distributed-systems concepts studied in class.

The exam statement is in [EXAM.md](EXAM.md).

## Architecture

The user creates a trip through `trip-service`. The trip service calls:

- `flight-service` over HTTP to book a flight;
- `hotel-service` over HTTP to reserve a room;
- `payment-service` over HTTP to authorize a fake payment;
- RabbitMQ to publish a `trip.confirmed` event consumed by `notification-worker`.

Each service owns its own PostgreSQL database. The trip service does not directly read or write the other services' databases.

## Run

```bash
docker compose up --build -d
```

No local Python installation is required. Scripts and tests run inside the Compose `tools` container.

Service URLs:

- trip-service: http://localhost:8000
- flight-service: http://localhost:8001
- hotel-service: http://localhost:8002
- payment-service: http://localhost:8003
- notification-api: http://localhost:8004
- RabbitMQ management: http://localhost:15672
- PostgreSQL: localhost:5432

Main API docs:

```text
http://localhost:8000/docs
```

### Port conflicts

The stack binds local ports `5432`, `5672`, `8000`-`8004`, and `15672`. If `docker compose up` fails with a bind error, stop or reconfigure any local PostgreSQL, RabbitMQ, or other development service already using one of those ports.

## Reset

```bash
docker compose run --rm tools python scripts/reset_all.py
```

This resets service data and purges the notification queue. If you change table definitions, add database constraints, or add indexes, recreate the PostgreSQL volume so existing tables are rebuilt:

```bash
docker compose down -v
docker compose up --build -d
```

## Demo Scripts

```bash
docker compose run --rm tools python scripts/smoke_success.py
docker compose run --rm tools python scripts/demo_overbooking.py
docker compose run --rm tools python scripts/demo_duplicate_request.py
docker compose run --rm tools python scripts/demo_partial_failure.py
docker compose run --rm tools python scripts/demo_duplicate_notification.py
docker compose run --rm tools python scripts/print_state.py
```

## Tests

With services running:

```bash
docker compose run --rm tools pytest
```

The provided intentional-flaw tests are baseline characterization tests. If you fix one of those flaws, update or replace the corresponding test so it verifies the new behavior.

Stop the stack with:

```bash
docker compose down
```

## Intentional Weaknesses

- Flight and hotel inventory checks can race.
- Duplicate trip requests create duplicate trips and side effects.
- Payment failure after resource reservation does not trigger compensation.
- Notification events are consumed without deduplication.
- Events are published directly, without a transactional outbox.
- There is no sharding, caching, replica-lag simulation, quorum logic, GraphQL, or gRPC.

## Exam requirements

The exam requires **at least 4 accepted concepts**:

- two concepts from Category A - Local correctness;
- one concept from Category B - Distributed workflow or messaging;
- one concept from Category C - Communication, consistency, or scaling.

Bonus concepts are ignored unless the 4 required concepts are already accepted.

Category A is split into:

- A1 - Integrity and atomicity: database transaction, database constraints;
- A2 - Concurrency control: pessimistic locking, optimistic locking, isolation-level handling, conflict detection and retry.

Category B includes concepts such as saga with durable state, compensation, TCC, simplified two-phase commit, and duplicate-message handling.

Category C includes concepts such as RPC-style communication, GraphQL gateway, idempotency key, retry-safe remote call, caching with a freshness policy, sharding, read-your-writes behavior, replica-lag simulation, quorum simulation, and hotspot mitigation.

For limited-surface concepts such as idempotency keys, the expected implementation must be complete and durable. For retry-safe calls, retries must not create duplicate side effects.

You must document your work by adding a `## Exam refactor` section to this README and by creating one concept card per implemented concept under `docs/concepts/`.

Do not assume the starter app is correct. Its flaws are the point of the exercise.
