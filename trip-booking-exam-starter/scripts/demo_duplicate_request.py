# Inside scripts/demo_duplicate_request.py
import httpx
import uuid
import sys
from common import reset_all, pretty, get_state

# Target the internal trip-service container inside the docker compose network
URL = "http://trip-service:8000/trips"

def main() -> None:
    print("Resetting databases...")
    reset_all()

    # Generate a single unique tracking key for this twin-request session
    shared_key = str(uuid.uuid4())
    headers = {"X-Idempotency-Key": shared_key}

    # Using the exact payload values matching your system's pre-seeded inventories
    payload = {
        "user_id": "user-1",
        "traveler_name": "Ada Lovelace",
        "flight_id": "FL-MANY-SEATS",
        "hotel_id": "HT-MANY-ROOMS",
        "nights": 2,
        "simulate": {}
    }

    print("==================================================")
    print("    RUNNING IDEMPOTENCY DEMO (DUPLICATE REQUEST)  ")
    print("==================================================")

    # --- FIRST CALL: Executes the entire booking pipeline ---
    print(f"\n[Call 1] Sending initial request with Key: {shared_key}")
    try:
        r1 = httpx.post(URL, json=payload, headers=headers)
        print(f"[Call 1] Status Code: {r1.status_code}")
        print(f"[Call 1] Trip ID Created: {r1.json().get('id')}")
        print(f"[Call 1] Workflow Status: {r1.json().get('status')}")
    except Exception as e:
        print(f"Call 1 connection failed: {e}")
        sys.exit(1)

    # --- SECOND CALL: Simulates a network retry / duplicate click ---
    print(f"\n[Call 2] Sending duplicate request with identical key string...")
    r2 = httpx.post(URL, json=payload, headers=headers)
    print(f"[Call 2] Status Code: {r2.status_code}")
    
    if r2.status_code == 201:
        print(f"[Call 2] Cache Hit! Saved Response Payload Safely Returned.")
        print(f"[Call 2] Trip ID Matches Call 1: {r2.json().get('id')}")

    # --- VERIFICATION LOOKUP ---
    print("\n==================================================")
    if r1.json().get('id') == r2.json().get('id') and r2.status_code == 201:
        print("          DEMO RESULT: SUCCESS (Category C Valid) ")
        print("==================================================")
        
        # Print the final state using the instructor's pretty print tool
        print("\nFinal Microservices State:")
        print(pretty(get_state()))
        sys.exit(0)
    else:
        print("          DEMO RESULT: FAILED                     ")
        print("==================================================")
        sys.exit(1)

if __name__ == "__main__":
    main()  