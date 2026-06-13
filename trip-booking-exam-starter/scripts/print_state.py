from common import get_state, pretty


def main() -> None:
    state = get_state()
    print("Trips")
    print(pretty(state["trip-service"]["trips"]))
    print("Flights")
    print(pretty(state["flight-service"]["flights"]))
    print("Flight bookings")
    print(pretty(state["flight-service"]["flight_bookings"]))
    print("Hotels")
    print(pretty(state["hotel-service"]["hotels"]))
    print("Hotel reservations")
    print(pretty(state["hotel-service"]["hotel_reservations"]))
    print("Payments")
    print(pretty(state["payment-service"]["payment_authorizations"]))
    print("Notifications")
    print(pretty(state["notification-api"]["notifications"]))


if __name__ == "__main__":
    main()

