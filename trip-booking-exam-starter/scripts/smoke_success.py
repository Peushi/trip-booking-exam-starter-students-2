from common import create_trip, get_state, pretty, reset_all, wait_for_notifications


def main() -> None:
    print("Resetting services...")
    reset_all()

    response = create_trip(
        {
            "user_id": "user-1",
            "traveler_name": "Ada Lovelace",
            "flight_id": "FL-MANY-SEATS",
            "hotel_id": "HT-MANY-ROOMS",
            "nights": 2,
            "simulate": {},
        }
    )
    response.raise_for_status()
    trip = response.json()
    print("Created trip:")
    print(pretty(trip))

    notifications = wait_for_notifications(trip["id"])
    state = get_state()
    print("Flight state:")
    print(pretty(state["flight-service"]))
    print("Hotel state:")
    print(pretty(state["hotel-service"]))
    print("Payment state:")
    print(pretty(state["payment-service"]))
    print("Notifications:")
    print(pretty(notifications))


if __name__ == "__main__":
    main()

