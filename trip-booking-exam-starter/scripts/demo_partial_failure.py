from common import base_trip_payload, create_trip, get_state, pretty, reset_all


def main() -> None:
    reset_all()
    response = create_trip(base_trip_payload(payment_force_decline=True))

    print("Payment failed after flight and hotel succeeded.")
    print("The trip is FAILED, but resources remain reserved.")
    print("This demonstrates the need for a saga, TCC, or another recovery mechanism.")
    print("Trip response:")
    print(pretty(response.json()))
    print("State:")
    print(pretty(get_state()))


if __name__ == "__main__":
    main()

