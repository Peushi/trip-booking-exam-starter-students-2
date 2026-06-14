# Database Constraints

## Category

A — A1 (Integrity and atomicity)

## Problem

In the baseline application, inventory validity is enforced only at the application
level. Nothing at the database level prevents `seats_available` or `rooms_available`
from going negative, or a booking from being created with zero or negative seats.
If the application check is bypassed, misconfigured, or races under concurrency,
the database will accept any integer value including invalid ones.

## Invariant or guarantee

The database enforces the following at all times, regardless of application logic:

- seat inventory can never go negative
- flight price must be positive
- a booking must cover at least one seat
- room inventory can never go negative
- hotel price must be positive
- a reservation must be for at least one night
- a reservation must cover at least one room


## Modified files

- `flight_service/db.py` — CHECK constraints added to `flights` and `flight_bookings`
- `hotel_service/db.py` — CHECK constraints added to `hotels` and `hotel_reservations`

## Behavior before

A direct SQL UPDATE or a bug in the application decrement logic could set
`seats_available` to -1 or lower. The database would accept it silently.
Similarly, a booking with `seats = 0` would be stored without error.

## Behavior after

Any write that violates a constraint is rejected by PostgreSQL with an
`asyncpg.exceptions.CheckViolationError`. The application receives an exception,
the write is not committed, and the invalid state is never stored.


## How to test

```bash
docker compose down -v
docker compose up --build -d
docker compose run --rm tools pytest tests/test_constraints.py -v
```

`docker compose down -v` is required because the tables already exist without
constraints. The volume must be dropped so PostgreSQL recreates the tables with
the new schema.

The test directly executes SQL against the flight and hotel databases to attempt
constraint-violating writes and asserts that a `CheckViolationError` is raised.

## Limitation

CHECK constraints protect the database layer only. They do not prevent the
application from attempting invalid writes — they only ensure such writes are
rejected. The caller still receives an unhandled 500 error unless the application
catches `CheckViolationError` explicitly and returns a meaningful response.
