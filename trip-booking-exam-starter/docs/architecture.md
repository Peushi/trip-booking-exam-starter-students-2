# Architecture

```text
                       ┌────────────────┐
                       │    Client      │
                       └───────┬────────┘
                               │
                               ▼
                       ┌────────────────┐
                       │  trip-service  │
                       │    trip_db     │
                       └───┬────┬────┬──┘
                           │    │    │
              HTTP         │    │    │ HTTP
                           │    │    │
        ┌──────────────────┘    │    └──────────────────┐
        ▼                       ▼                       ▼
┌────────────────┐      ┌────────────────┐      ┌────────────────┐
│ flight-service │      │ hotel-service  │      │ payment-service│
│   flight_db    │      │    hotel_db    │      │   payment_db   │
└────────────────┘      └────────────────┘      └────────────────┘

                       RabbitMQ event
                              │
                              ▼
                    ┌────────────────────┐
                    │ notification-worker │
                    │  notification_db    │
                    └────────────────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │  notification-api   │
                    └────────────────────┘
```

Each service owns its database. Cross-service communication is HTTP except for trip-confirmation notifications, which use RabbitMQ.

