"""Enrichment Pipeline for HoneyBadger.

Subscribes to raw bus, enriches events (GeoIP, MITRE, credentials, payloads),
persists to PostgreSQL, and publishes to enriched bus.
"""

import asyncio
import logging
import time
from typing import Callable, Optional

from bus import EventBus
from geoip import GeoIpProvider
from metrics import (
    record_event,
    record_geoip_cache_hit,
    record_geoip_cache_miss,
    record_geoip_lookup,
    record_pipeline_error,
    record_pipeline_latency,
    record_storage_write,
)
from mitre import classify
from schemas import EnrichedEvent, RawEvent
from storage import Storage

logger = logging.getLogger(__name__)


class EnrichmentPipeline:
    """Orchestrates event enrichment: geoip -> mitre -> credentials -> payloads -> storage."""

    def __init__(
        self,
        raw_bus: EventBus[RawEvent],
        enriched_bus: EventBus[EnrichedEvent],
        storage: Storage,
        geoip: GeoIpProvider,
        credential_tracker,
        payload_tracker,
    ) -> None:
        self._raw_bus = raw_bus
        self._enriched_bus = enriched_bus
        self._storage = storage
        self._geoip = geoip
        self._credential_tracker = credential_tracker
        self._payload_tracker = payload_tracker
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the pipeline consumer."""
        if self._running:
            logger.warning("Pipeline already running")
            return

        self._running = True
        self._raw_bus.subscribe(self._process_event)
        self._task = asyncio.create_task(self._raw_bus.start(), name="enrichment-pipeline")
        logger.info("Enrichment pipeline started")

    async def stop(self) -> None:
        """Stop the pipeline consumer."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._raw_bus.stop()
        logger.info("Enrichment pipeline stopped")

    async def _process_event(self, raw_event: RawEvent) -> None:
        """Process a single raw event through the enrichment pipeline."""
        start_time = time.time()
        try:
            # 1. GeoIP enrichment
            geo_info = None
            geoip_start = time.time()
            if raw_event.source_ip:
                geo_info = await self._geoip.lookup(str(raw_event.source_ip))
            # GeoIP metrics are recorded in the provider

            # 2. MITRE ATT&CK classification
            technique_id, severity = classify(raw_event)

            # 3. Create enriched event
            enriched = EnrichedEvent(
                service=raw_event.service,
                source_ip=raw_event.source_ip,
                destination_ip=raw_event.destination_ip,
                timestamp=raw_event.timestamp,
                login_info=raw_event.login_info,
                user_agent=raw_event.user_agent,
                http_method=raw_event.http_method,
                http_path=raw_event.http_path,
                http_status_code=raw_event.http_status_code,
                command=raw_event.command,
                payload_url=raw_event.payload_url,
                payload_hash=raw_event.payload_hash,
                payload_size=raw_event.payload_size,
                source_port=raw_event.source_port,
                destination_port=raw_event.destination_port,
                additional_info=raw_event.additional_info,
                geo_info=geo_info,
                technique_id=technique_id,
                severity=severity,
            )

            # 4. Credential tracking (for auth events)
            if raw_event.login_info and raw_event.login_info.username and raw_event.login_info.password_hash:
                await self._credential_tracker.process(raw_event)

            # 5. Payload tracking (for wget/curl commands)
            if raw_event.payload_url:
                await self._payload_tracker.process(raw_event)

            # 6. Persist to PostgreSQL
            storage_start = time.time()
            await self._storage.events.insert(enriched)
            record_storage_write("insert", time.time() - storage_start)

            # 7. Publish to enriched bus for API/WebSocket consumers
            self._enriched_bus.publish(enriched)

            # Record event metric
            record_event(
                service=raw_event.service.value,
                technique=technique_id,
                severity=severity.value if severity else None,
            )

            # Record payload metrics
            if raw_event.payload_url:
                record_payload_captured(raw_event.payload_size)

            # Record pipeline latency
            record_pipeline_latency(time.time() - start_time)

            logger.debug(
                "Enriched event: service=%s ip=%s technique=%s severity=%s",
                enriched.service.value,
                enriched.source_ip,
                technique_id,
                severity.value if severity else "none",
            )

        except Exception as e:
            logger.exception("Pipeline error processing event: %s", e)
            record_pipeline_error("process_event")
            # Don't re-raise - we don't want to crash the pipeline
            # The event is logged but not enriched/persisted