# Student Guide

## 1. What the system does

The application books a trip composed of a flight, hotel room, payment authorization, and notification. It works on the happy path but has deliberate correctness problems.

## 2. What services exist

- `trip-service`: orchestrates booking requests.
- `flight-service`: owns flight inventory and flight bookings.
- `hotel-service`: owns hotel inventory and reservations.
- `payment-service`: creates fake payment authorizations.
- `notification-api`: exposes stored notifications.
- `notification-worker`: consumes RabbitMQ trip events and stores notifications.

## 3. Normal booking flow

1. A client posts to `POST /trips`.
2. `trip-service` creates a `PENDING` trip.
3. It books a flight through `flight-service`.
4. It reserves a room through `hotel-service`.
5. It computes the total amount.
6. It authorizes a fake payment through `payment-service`.
7. It marks the trip `CONFIRMED`.
8. It publishes a `trip.confirmed` event.
9. `notification-worker` stores a notification.

## 4. Useful endpoints

Every HTTP service has:

- `GET /health`
- `POST /admin/reset`
- `GET /debug/state`

Main endpoints:

- `POST /trips`
- `GET /trips`
- `GET /flights`
- `POST /flights/{flight_id}/bookings`
- `GET /hotels`
- `POST /hotels/{hotel_id}/reservations`
- `POST /payments/authorizations`
- `GET /notifications`

## 5. Demo scripts

Run these after `docker compose up --build -d`.
You do not need Python installed locally; the commands run inside Docker:

```bash
docker compose run --rm tools python scripts/smoke_success.py
docker compose run --rm tools python scripts/demo_overbooking.py
docker compose run --rm tools python scripts/demo_duplicate_request.py
docker compose run --rm tools python scripts/demo_partial_failure.py
docker compose run --rm tools python scripts/demo_duplicate_notification.py
docker compose run --rm tools python scripts/print_state.py
```

## 6. Known weaknesses

The flight service checks availability and later decrements it. Under concurrent requests, several clients may pass the check before any update is visible.

The hotel service has the same inventory problem for rooms.

The trip service has no idempotency key. If a client retries the same logical operation, a new trip and new side effects are created.

The booking flow has no compensation. If payment fails after flight and hotel success, those resources remain reserved.

The notification worker stores one row per consumed message. If the same event is delivered twice, two notifications are stored.

The trip service publishes events directly after updating the trip. There is no mechanism that atomically persists the state change and the message.

## 7. Adding dependencies

If your implementation requires additional Python packages, add them to `requirements.txt` and rebuild the containers with:

```bash
docker compose up --build -d
```

The Docker image installs dependencies from `requirements.txt`, so changing only your local environment is not enough.

## 8. Troubleshooting

To completely reset the application, including databases and Docker volumes, run:

```bash
docker compose down -v
docker compose up --build -d
```

This deletes the local database state. Use it when you are stuck, when your schema changes are not applied, or when you want to restart from a clean environment.

If you are still stuck, contact me on Teams.

## 9. Suggested places to extend the code

- Local correctness: `flight_service/main.py`, `hotel_service/main.py`
- Trip workflow: `trip_service/main.py`
- Idempotency: `trip_service/db.py`, `trip_service/main.py`
- Messaging: `trip_service/events.py`, `notification_worker/worker.py`, `notification_api/db.py`
- API style experiments: `trip_service/clients.py`
- State and scaling experiments: service `db.py` files
