# Database Transaction

## Category

A — A1 (Integrity and atomicity)

## Problem

In the baseline application, the inventory decrement and the booking row insertion
are two separate SQL statements executed without a transaction.

If the process crashes, raises an exception, or is killed between statements 1 and 2,
the seat is permanently lost: `seats_available` is decremented but no
`flight_bookings` row exists. The same problem exists in `hotel-service` for rooms
and reservations. The cancellation paths have the same issue in reverse: the
reservation status can be set to CANCELLED without the inventory being restored.

## Invariant or guarantee

For every confirmed booking or reservation, exactly one inventory decrement and
exactly one booking row exist. For every cancellation, exactly one status update
and exactly one inventory restore exist. Neither half of either operation can
be committed without the other.

## Modified files

- `flight_service/main.py` — `book_flight` and `cancel_booking` endpoints
- `hotel_service/main.py` — `reserve_hotel` and `cancel_reservation` endpoints

## Behavior before

A forced failure injected between the inventory decrement and the booking insert
(via `fail_after_decrement=True`) leaves `seats_available` permanently decremented
with no corresponding `flight_bookings` row. The state is internally inconsistent.

## Behavior after

The decrement and the insert are wrapped in `async with conn.transaction()`.
Raising an exception inside the block triggers an automatic rollback. Both
statements succeed together or neither is committed. The same protection applies
to the cancellation path in both services.

## How to test

```bash
docker compose run --rm tools pytest tests/test_transaction.py -v
```

The test calls `POST /flights/FL-ONE-SEAT/bookings` with `fail_after_decrement=True`,
which injects a forced exception after the decrement but inside the transaction.
It then reads `debug/state` and asserts that `seats_available` is unchanged (still 1)
and that no `flight_bookings` row was created.

## Limitation

The transaction protects local atomicity within a single service. It does not protect
against partial failure across services.