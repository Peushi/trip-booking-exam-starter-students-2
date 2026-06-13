from common import base_trip_payload, create_trip, get_state, pretty, reset_all


def main() -> None:
    reset_all()
    response = create_trip(base_trip_payload(payment_force_decline=True))

    print("Payment failed after flight and hotel succeeded.")
    print("The saga compensated the completed steps.")
    print("The trip is CANCELLED, and flight/hotel resources were released.")
    print("This demonstrates a durable saga state machine with compensation.")  
    print("Trip response:")
    print(pretty(response.json()))
    print("State:")
    print(pretty(get_state()))


if __name__ == "__main__":
    main()

