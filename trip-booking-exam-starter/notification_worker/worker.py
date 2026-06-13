from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from uuid import UUID

from notification_worker import db
from shared.logging import configure_logging
from shared.rabbitmq import connect, ensure_notification_queue

SERVICE_NAME = "notification-worker"
CRASH_MARKER = Path("/tmp/notification_worker_crashed_once")


async def handle_message(message) -> None:
    async with message.process(requeue=True):
        event = json.loads(message.body.decode("utf-8"))
        await db.insert_notification(
            event_id=UUID(event["event_id"]),
            trip_id=UUID(event["trip_id"]),
            user_id=event["user_id"],
            notification_type=event["event_type"],
            payload=event,
        )

        if os.getenv("CRASH_ONCE_AFTER_INSERT_BEFORE_ACK", "false").lower() == "true" and not CRASH_MARKER.exists():
            CRASH_MARKER.write_text("crashed\n", encoding="utf-8")
            logging.error("Crashing after insert before ack, by request")
            os._exit(1)


async def main() -> None:
    configure_logging(SERVICE_NAME)
    await db.connect_with_retry()
    await db.init_db()

    connection = await connect()
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await ensure_notification_queue(channel)
    logging.info("Waiting for trip.confirmed events")
    await queue.consume(handle_message)

    try:
        await asyncio.Future()
    finally:
        await connection.close()
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())

