import asyncio

import httpx

from common import SERVICES, purge_notification_queue


def main() -> None:
    print("Purging notification queue... ", end="")
    asyncio.run(purge_notification_queue())
    print("ok")

    with httpx.Client(timeout=10) as client:
        for name, base_url in SERVICES:
            print(f"Resetting {name}... ", end="")
            response = client.post(f"{base_url}/admin/reset")
            response.raise_for_status()
            print("ok")


if __name__ == "__main__":
    main()
