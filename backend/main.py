"""HoneyBadger backend entrypoint (Slice 1: SSH honeypot + console sink)."""

import asyncio
import contextlib
import logging

from bus import EventBus
from config import get_settings
from schemas import RawEvent
from sshd import start_ssh_server

logger = logging.getLogger(__name__)


async def console_sink(event: RawEvent) -> None:
    """Print each raw event as one JSON line so a dashboard can tail it."""
    print(event.model_dump_json(), flush=True)


async def run() -> None:
    settings = get_settings()

    bus: EventBus[RawEvent] = EventBus("raw")
    bus.subscribe(console_sink)
    await bus.start()

    server = await start_ssh_server(settings, bus)
    logger.info(
        "SSH honeypot listening on %s:%s", settings.ssh_host, settings.ssh_port
    )

    try:
        await asyncio.Event().wait()
    finally:
        server.close()
        with contextlib.suppress(Exception):
            await server.wait_closed()
        await bus.stop()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("asyncssh").setLevel(logging.WARNING)

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run())


if __name__ == "__main__":
    main()
