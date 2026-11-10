"""Credential extraction and tracking (hashes only, top-N counters).

Implements the hash-only policy: plaintext passwords never touch disk.
Only SHA-256 hashes are stored, with aggregate counters for the dashboard.
"""

import logging
from collections import Counter
from typing import Optional

from metrics import record_top_credential_count, record_unique_credentials
from schemas import RawEvent
from storage import CredentialRepository

logger = logging.getLogger(__name__)


class CredentialTracker:
    """Tracks credential attempts with in-memory counters + DB persistence.

    Maintains top-N credential pairs for the dashboard. Only hashes are stored.
    """

    def __init__(self, repo: CredentialRepository, top_n: int = 10) -> None:
        self._repo = repo
        self._top_n = top_n
        self._counter: Counter[tuple[str, str]] = Counter()

    async def process(self, event: RawEvent) -> None:
        """Process an event for credential tracking."""
        if not event.login_info:
            return

        username = event.login_info.username
        password_hash = event.login_info.password_hash

        if not username or not password_hash:
            return

        # Validate hash format (should already be validated by schema)
        if not password_hash.startswith("sha256:"):
            logger.warning("Invalid password hash format: %s", password_hash[:20])
            return

        key = (username, password_hash)
        self._counter[key] += 1

        # Update metrics
        record_unique_credentials(len(self._counter))
        if self._counter[key] > 0:
            # Get the max count
            max_count = max(self._counter.values()) if self._counter else 0
            record_top_credential_count(max_count)

        # Persist to database
        try:
            await self._repo.increment(username, password_hash)
        except Exception as e:
            logger.error("Failed to persist credential count: %s", e)

    async def get_top_n(self, n: Optional[int] = None) -> list[dict]:
        """Get top N credential pairs by attempt count."""
        limit = n or self._top_n
        return await self._repo.top_n(limit)

    def get_local_top_n(self, n: Optional[int] = None) -> list[dict]:
        """Get top N from local counter (for real-time dashboard updates)."""
        limit = n or self._top_n
        return [
            {
                "username": username,
                "password_hash": password_hash,
                "count": count,
            }
            for (username, password_hash), count in self._counter.most_common(limit)
        ]

    def get_total_attempts(self) -> int:
        """Get total credential attempts tracked locally."""
        return sum(self._counter.values())

    def get_unique_credentials(self) -> int:
        """Get number of unique credential pairs seen."""
        return len(self._counter)