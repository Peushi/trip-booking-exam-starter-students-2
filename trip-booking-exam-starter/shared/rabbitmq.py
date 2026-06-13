from __future__ import annotations

import json
import os
from typing import Any

import aio_pika

EXCHANGE_NAME = "trip-events"
TRIP_CONFIRMED_ROUTING_KEY = "trip.confirmed"
NOTIFICATION_QUEUE = "notification-service.trip-confirmed"


def rabbitmq_url() -> str:
    return os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")


async def connect() -> aio_pika.RobustConnection:
    return await aio_pika.connect_robust(rabbitmq_url())


async def ensure_exchange(channel: aio_pika.abc.AbstractChannel) -> aio_pika.abc.AbstractExchange:
    return await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True)


async def ensure_notification_queue(channel: aio_pika.abc.AbstractChannel) -> aio_pika.abc.AbstractQueue:
    exchange = await ensure_exchange(channel)
    queue = await channel.declare_queue(NOTIFICATION_QUEUE, durable=True)
    await queue.bind(exchange, routing_key=TRIP_CONFIRMED_ROUTING_KEY)
    return queue


async def purge_notification_queue() -> None:
    connection = await connect()
    async with connection:
        channel = await connection.channel()
        queue = await ensure_notification_queue(channel)
        await queue.purge()


async def publish_trip_confirmed(event: dict[str, Any]) -> None:
    connection = await connect()
    async with connection:
        channel = await connection.channel()
        await ensure_notification_queue(channel)
        exchange = await ensure_exchange(channel)
        message = aio_pika.Message(
            body=json.dumps(event).encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await exchange.publish(message, routing_key=TRIP_CONFIRMED_ROUTING_KEY)
