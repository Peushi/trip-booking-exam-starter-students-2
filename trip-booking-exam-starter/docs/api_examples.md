# API Examples

Create a trip:

```bash
curl -s http://localhost:8000/trips \
  -H 'content-type: application/json' \
  -d '{
    "user_id": "user-1",
    "traveler_name": "Ada Lovelace",
    "flight_id": "FL-MANY-SEATS",
    "hotel_id": "HT-MANY-ROOMS",
    "nights": 2,
    "simulate": {}
  }'
```

Trigger a payment decline:

```bash
curl -s http://localhost:8000/trips \
  -H 'content-type: application/json' \
  -d '{
    "user_id": "user-1",
    "traveler_name": "Ada Lovelace",
    "flight_id": "FL-MANY-SEATS",
    "hotel_id": "HT-MANY-ROOMS",
    "nights": 2,
    "simulate": {"payment_force_decline": true}
  }'
```

Inspect service state:

```bash
curl -s http://localhost:8001/debug/state
curl -s http://localhost:8002/debug/state
curl -s http://localhost:8003/debug/state
curl -s http://localhost:8004/debug/state
```

