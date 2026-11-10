"""Retention manager for HoneyBadger.

Scheduled purge of events older than retention period (default 180 days).
Also purges expired GeoIP cache entries.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

from config import Settings
from metrics import (
    record_retention_run,
    record_retention_deleted,
    record_retention_last_success,
)
from storage import Storage

logger = logging.getLogger(__name__)


class RetentionManager:
    """Manages scheduled data retention purging."""

    def __init__(self, storage: Storage, settings: Settings) -> None:
        self._storage = storage
        self._settings = settings
        self._retention_days = settings.retention_days
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start the retention scheduler."""
        if self._running:
            logger.warning("Retention manager already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="retention-manager")
        logger.info("Retention manager started (retention: %d days)", self._retention_days)

    async def stop(self) -> None:
        """Stop the retention scheduler."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Retention manager stopped")

    async def _run_loop(self) -> None:
        """Main loop: run purge daily at 03:00 UTC."""
        while self._running:
            try:
                await self._wait_until_next_run()
                if not self._running:
                    break
                await self._purge()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Retention job failed: %s", e)
                record_retention_run("error")
                # Wait an hour before retrying on error
                await asyncio.sleep(3600)

    async def _wait_until_next_run(self) -> None:
        """Sleep until 03:00 UTC next day."""
        now = datetime.now(timezone.utc)
        next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)

        sleep_seconds = (next_run - now).total_seconds()
        logger.debug("Next retention run in %.0f seconds", sleep_seconds)
        await asyncio.sleep(sleep_seconds)

    async def _purge(self) -> None:
        """Execute the purge operation."""
        logger.info("Starting retention purge (older than %d days)", self._retention_days)
        start_time = time.time()

        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)

        try:
            total_deleted = 0

            # Purge old events
            events_deleted = await self._purge_events(cutoff)
            total_deleted += events_deleted
            record_retention_deleted("events", events_deleted)

            # Purge expired GeoIP cache entries
            geoip_deleted = await self._storage.geoip_cache.purge_expired()
            total_deleted += geoip_deleted
            record_retention_deleted("geoip_cache", geoip_deleted)

            # Purge old credential counts (keep only last 90 days of credential data)
            cred_cutoff = datetime.now(timezone.utc) - timedelta(days=90)
            cred_deleted = await self._purge_credential_counts(cred_cutoff)
            total_deleted += cred_deleted
            record_retention_deleted("credential_counts", cred_deleted)

            # Purge old payloads (keep only last 365 days)
            payload_cutoff = datetime.now(timezone.utc) - timedelta(days=365)
            payload_deleted = await self._purge_payloads(payload_cutoff)
            total_deleted += payload_deleted
            record_retention_deleted("payloads", payload_deleted)

            duration = time.time() - start_time
            record_retention_run("success")
            record_retention_last_success(time.time())

            logger.info(
                "Retention purge completed in %.2fs: %d total rows deleted "
                "(events=%d, geoip=%d, credentials=%d, payloads=%d)",
                duration,
                total_deleted,
                events_deleted,
                geoip_deleted,
                cred_deleted,
                payload_deleted,
            )

        except Exception as e:
            logger.exception("Retention purge failed: %s", e)
            record_retention_run("error")
            raise

    async def _purge_events(self, cutoff: datetime) -> int:
        """Delete events older than cutoff."""
        async with self._storage.session() as session:
            from db.models import Event
            from sqlalchemy import delete

            stmt = delete(Event).where(Event.ts < cutoff)
            result = await session.execute(stmt)
            return result.rowcount

    async def _purge_credential_counts(self, cutoff: datetime) -> int:
        """Delete credential counts older than cutoff."""
        async with self._storage.session() as session:
            from db.models import CredentialCount
            from sqlalchemy import delete

            stmt = delete(CredentialCount).where(CredentialCount.last_seen < cutoff)
            result = await session.execute(stmt)
            return result.rowcount

    async def _purge_payloads(self, cutoff: datetime) -> int:
        """Delete payloads older than cutoff (only non-quarantined)."""
        async with self._storage.session() as session:
            from db.models import Payload
            from sqlalchemy import delete

            stmt = delete(Payload).where(
                Payload.first_seen < cutoff, Payload.quarantined == False  # noqa: E712
            )
            result = await session.execute(stmt)
            return result.rowcount

    async def run_once(self) -> dict:
        """Run purge once manually (for testing/admin). Returns stats."""
        await self._purge()
        return {"status": "completed"}