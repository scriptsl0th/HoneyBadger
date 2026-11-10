"""HoneyBadger backend entrypoint - Full stack with enrichment pipeline."""

import asyncio
import contextlib
import logging
import time

from api import start_api_server
from bus import EventBus
from config import get_settings
from credentials import CredentialTracker
from geoip import create_geoip_provider
from httpd import HttpHoneypot
from metrics import record_uptime, set_info, start_metrics_server
from pipeline import EnrichmentPipeline
from payloads import PayloadTracker
from retention import RetentionManager
from schemas import EnrichedEvent, RawEvent
from sshd import start_ssh_server
from storage import Storage

logger = logging.getLogger(__name__)

_START_TIME = time.time()
_VERSION = "0.2.0"
_BUILD_DATE = "2026-11-10"


async def run() -> None:
    settings = get_settings()

    # Set build info metric
    set_info(_VERSION, _BUILD_DATE)

    # 1. Create buses
    raw_bus: EventBus[RawEvent] = EventBus("raw")
    enriched_bus: EventBus[EnrichedEvent] = EventBus("enriched")

    # 2. Initialize storage (PostgreSQL)
    storage = Storage(settings.database_url)
    await storage.init()

    # 3. Start metrics server
    start_metrics_server(settings.metrics_port)

    # 4. Create enrichment components
    geoip = create_geoip_provider(settings, storage.geoip_cache)
    credentials = CredentialTracker(storage.credentials, top_n=10)
    payloads = PayloadTracker(storage.payloads, settings)

    # 5. Start enrichment pipeline
    pipeline = EnrichmentPipeline(
        raw_bus=raw_bus,
        enriched_bus=enriched_bus,
        storage=storage,
        geoip=geoip,
        credential_tracker=credentials,
        payload_tracker=payloads,
    )
    await pipeline.start()

    # 6. Start retention manager
    retention = RetentionManager(storage, settings)
    await retention.start()

    # 7. Start SSH honeypot
    ssh_server = await start_ssh_server(settings, raw_bus)
    logger.info(
        "SSH honeypot listening on %s:%s", settings.ssh_host, settings.ssh_port
    )

    # 8. Start HTTP honeypot
    http_server = HttpHoneypot(settings, raw_bus)
    await http_server.start()
    logger.info(
        "HTTP honeypot listening on %s:%s", settings.http_host, settings.http_port
    )

    # 9. Start API server (REST + WebSocket) with enriched bus and storage
    api_runner = await start_api_server(settings, enriched_bus, storage)
    logger.info(
        "API + WebSocket listening on %s:%s", settings.api_host, settings.api_port
    )

    # 10. Start uptime reporting task
    uptime_task = asyncio.create_task(_report_uptime(), name="uptime-reporter")

    # 11. Start event count reporting task
    event_count_task = asyncio.create_task(_report_event_count(storage), name="event-count-reporter")

    logger.info("HoneyBadger backend fully started (version %s)", _VERSION)

    try:
        await asyncio.Event().wait()
    finally:
        logger.info("Shutting down...")
        uptime_task.cancel()
        event_count_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await uptime_task
            await event_count_task

        await http_server.stop()
        ssh_server.close()
        with contextlib.suppress(Exception):
            await ssh_server.wait_closed()

        await pipeline.stop()
        await retention.stop()
        await geoip.close()
        await payloads.close()
        await storage.close()
        await api_runner.cleanup()
        await raw_bus.stop()
        await enriched_bus.stop()
        logger.info("Shutdown complete")


async def _report_uptime() -> None:
    """Periodically report uptime metric."""
    from metrics import record_uptime

    while True:
        await asyncio.sleep(60)
        record_uptime(time.time() - _START_TIME)


async def _report_event_count(storage: Storage) -> None:
    """Periodically report total event count metric."""
    while True:
        await asyncio.sleep(300)  # Every 5 minutes
        await storage.update_event_count()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("asyncssh").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run())


if __name__ == "__main__":
    main()