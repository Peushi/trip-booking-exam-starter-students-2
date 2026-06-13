from common import base_trip_payload, create_trip, pretty, reset_all, wait_for_notifications


def main() -> None:
    reset_all()
    response = create_trip(base_trip_payload(publish_event_twice=True))
    response.raise_for_status()
    trip = response.json()
    notifications = wait_for_notifications(trip["id"], minimum=2, timeout_seconds=8)

    print("The notification worker processed the same event more than once.")
    print("Because it has no idempotency mechanism, duplicate notifications were stored.")
    print("Notifications:")
    print(pretty(notifications))


if __name__ == "__main__":
    main()

