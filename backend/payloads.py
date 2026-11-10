"""Payload metadata capture and optional quarantine.

Records URL, hash, and size of payloads from wget/curl commands.
NEVER fetches or executes attacker-supplied URLs by default.
Optional CAPTURE_PAYLOADS=enabled stages files to a noexec quarantine directory.
"""

import hashlib
import logging
import os
import pathlib
import subprocess
from typing import Optional

import aiohttp

from config import Settings
from metrics import record_payload_captured, record_payload_quarantined
from schemas import RawEvent
from storage import PayloadRepository

logger = logging.getLogger(__name__)


class PayloadTracker:
    """Tracks payload metadata and optionally quarantines payloads."""

    def __init__(
        self,
        repo: PayloadRepository,
        settings: Settings,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self._repo = repo
        self._settings = settings
        self._session = session
        self._owns_session = session is None
        self._capture_enabled = settings.capture_payloads
        self._quarantine_dir = pathlib.Path(settings.quarantine_dir)

        # Ensure quarantine directory exists with noexec if capturing
        if self._capture_enabled:
            self._setup_quarantine()

    def _setup_quarantine(self) -> None:
        """Create quarantine directory with noexec mount if possible."""
        try:
            self._quarantine_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            # Try to mount with noexec (requires root, may fail in container)
            try:
                subprocess.run(
                    ["mount", "-o", "remount,noexec", str(self._quarantine_dir)],
                    check=False,
                    capture_output=True,
                )
            except Exception:
                pass  # Non-fatal; log only
            logger.info("Payload quarantine enabled at %s", self._quarantine_dir)
        except Exception as e:
            logger.error("Failed to setup quarantine directory: %s", e)
            self._capture_enabled = False

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def process(self, event: RawEvent) -> None:
        """Process an event for payload tracking."""
        if not event.payload_url:
            return

        url = event.payload_url
        hash_ = event.payload_hash
        size = event.payload_size

        # If hash not provided but we have the URL, we could compute it
        # but we never fetch the URL by default

        # Record metadata to database
        try:
            await self._repo.upsert(url, hash_, size)
            record_payload_captured(size)
        except Exception as e:
            logger.error("Failed to persist payload metadata for %s: %s", url, e)

        # Optional: quarantine the payload (download to noexec dir)
        if self._capture_enabled and not hash_:
            await self._quarantine_payload(url)

    async def _quarantine_payload(self, url: str) -> Optional[str]:
        """Download payload to quarantine directory. Returns quarantine path or None."""
        if not self._capture_enabled:
            return None

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning("Failed to download payload for quarantine: %s (status %d)", url, response.status)
                    return None

                content = await response.read()

                # Compute hash
                hash_ = hashlib.sha256(content).hexdigest()
                size = len(content)

                # Determine filename
                filename = self._safe_filename(url, hash_)
                quarantine_path = self._quarantine_dir / filename

                # Write to quarantine (atomic write)
                temp_path = quarantine_path.with_suffix(quarantine_path.suffix + ".tmp")
                temp_path.write_bytes(content)
                temp_path.chmod(0o400)  # Read-only
                temp_path.rename(quarantine_path)

                # Update database with hash, size, and quarantine info
                await self._repo.upsert(url, hash_, size)
                await self._repo.mark_quarantined(url, str(quarantine_path))
                record_payload_quarantined()

                logger.info("Quarantined payload: %s -> %s (hash: %s, size: %d)", url, quarantine_path, hash_, size)
                return str(quarantine_path)

        except aiohttp.ClientError as e:
            logger.warning("Failed to quarantine payload %s: %s", url, e)
            return None
        except Exception as e:
            logger.exception("Unexpected error quarantining payload %s", url)
            return None

    @staticmethod
    def _safe_filename(url: str, hash_: str) -> str:
        """Generate a safe filename from URL and hash."""
        # Extract filename from URL
        from urllib.parse import urlparse

        parsed = urlparse(url)
        name = pathlib.Path(parsed.path).name

        # Sanitize
        safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_")
        safe_name = "".join(c if c in safe_chars else "_" for c in name)

        # Limit length and add hash prefix
        if len(safe_name) > 100:
            safe_name = safe_name[:100]

        return f"{hash_[:16]}_{safe_name}"

    async def close(self) -> None:
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()