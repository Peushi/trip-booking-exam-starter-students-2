from common import base_trip_payload, create_trip, get_state, pretty, reset_all


def main() -> None:
    reset_all()
    payload = base_trip_payload()

    first = create_trip(payload)
    second = create_trip(payload)

    print("Same logical user action submitted twice.")
    print("Because there is no idempotency key, the system created two trips.")
    print("First response:")
    print(pretty(first.json()))
    print("Second response:")
    print(pretty(second.json()))
    print("State:")
    print(pretty(get_state()))


if __name__ == "__main__":
    main()

