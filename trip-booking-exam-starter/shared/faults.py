import asyncio


async def maybe_delay(ms: int) -> None:
    if ms > 0:
        await asyncio.sleep(ms / 1000)


def failure_message(service: str, reason: str) -> str:
    return f"{service} deterministic failure: {reason}"

