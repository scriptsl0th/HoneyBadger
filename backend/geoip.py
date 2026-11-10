"""GeoIP Provider for IP geolocation enrichment.

Supports multiple providers: ip-api.com (default, free), MaxMind (opt-in), and Null (offline).
"""

import abc
import logging
from typing import Optional

import aiohttp

from config import Settings
from metrics import (
    record_geoip_cache_hit,
    record_geoip_cache_miss,
    record_geoip_lookup,
)
from schemas import GeoInfo
from storage import GeoIPCacheRepository

logger = logging.getLogger(__name__)


class GeoIpProvider(abc.ABC):
    """Abstract base class for GeoIP providers."""

    @abc.abstractmethod
    async def lookup(self, ip: str) -> Optional[GeoInfo]:
        """Look up geolocation for an IP address."""
        ...

    @abc.abstractmethod
    async def close(self) -> None:
        """Clean up resources."""
        ...


class IpApiProvider(GeoIpProvider):
    """GeoIP provider using ip-api.com (free, no key required, rate limited)."""

    BASE_URL = "http://ip-api.com/json/"

    def __init__(
        self,
        cache: GeoIPCacheRepository,
        settings: Settings,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self._cache = cache
        self._settings = settings
        self._session = session
        self._owns_session = session is None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=5)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def lookup(self, ip: str) -> Optional[GeoInfo]:
        # Check cache first
        cached = await self._cache.get(ip)
        if cached:
            logger.debug("GeoIP cache hit for %s", ip)
            record_geoip_cache_hit()
            record_geoip_lookup("ip-api", "hit")
            return cached

        # Fetch from ip-api.com
        logger.debug("GeoIP cache miss for %s, querying ip-api.com", ip)
        record_geoip_cache_miss()
        session = await self._get_session()

        try:
            url = f"{self.BASE_URL}{ip}"
            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning("ip-api.com returned %d for %s", response.status, ip)
                    record_geoip_lookup("ip-api", "error")
                    return None

                data = await response.json()
                if data.get("status") != "success":
                    logger.warning("ip-api.com lookup failed for %s: %s", ip, data.get("message"))
                    record_geoip_lookup("ip-api", "error")
                    return None

                info = GeoInfo(
                    country=data.get("country"),
                    region=data.get("regionName"),
                    city=data.get("city"),
                    latitude=data.get("lat"),
                    longitude=data.get("lon"),
                    asn=data.get("as"),
                )

                # Cache the result
                await self._cache.set(ip, info, self._settings.geoip_cache_ttl_days)
                record_geoip_lookup("ip-api", "miss")
                return info

        except aiohttp.ClientError as e:
            logger.warning("GeoIP lookup failed for %s: %s", ip, e)
            record_geoip_lookup("ip-api", "error")
            return None
        except Exception as e:
            logger.exception("Unexpected error during GeoIP lookup for %s", ip)
            record_geoip_lookup("ip-api", "error")
            return None

    async def close(self) -> None:
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()


class MaxMindProvider(GeoIpProvider):
    """GeoIP provider using MaxMind GeoLite2/GeoIP2 database (local, opt-in)."""

    def __init__(
        self,
        cache: GeoIPCacheRepository,
        settings: Settings,
    ) -> None:
        self._cache = cache
        self._settings = settings
        self._reader = None

        if not settings.maxmind_db_path:
            raise ValueError("MaxMind database path not configured")

    def _get_reader(self):
        if self._reader is None:
            try:
                import maxminddb

                self._reader = maxminddb.open_database(str(self._settings.maxmind_db_path))
            except ImportError:
                raise RuntimeError("maxminddb package not installed. Install with: pip install maxminddb")
            except Exception as e:
                raise RuntimeError(f"Failed to open MaxMind database: {e}")
        return self._reader

    async def lookup(self, ip: str) -> Optional[GeoInfo]:
        # Check cache first
        cached = await self._cache.get(ip)
        if cached:
            record_geoip_cache_hit()
            record_geoip_lookup("maxmind", "hit")
            return cached

        record_geoip_cache_miss()

        try:
            reader = self._get_reader()
            data = reader.get(ip)

            if not data:
                record_geoip_lookup("maxmind", "miss")
                return None

            info = GeoInfo(
                country=data.get("country", {}).get("names", {}).get("en"),
                region=data.get("subdivisions", [{}])[0].get("names", {}).get("en"),
                city=data.get("city", {}).get("names", {}).get("en"),
                latitude=data.get("location", {}).get("latitude"),
                longitude=data.get("location", {}).get("longitude"),
                asn=data.get("traits", {}).get("autonomous_system_organization"),
            )

            # Cache the result
            await self._cache.set(ip, info, self._settings.geoip_cache_ttl_days)
            record_geoip_lookup("maxmind", "miss")
            return info

        except Exception as e:
            logger.warning("MaxMind lookup failed for %s: %s", ip, e)
            record_geoip_lookup("maxmind", "error")
            return None

    async def close(self) -> None:
        if self._reader:
            self._reader.close()
            self._reader = None


class NullProvider(GeoIpProvider):
    """Null provider that returns no geolocation (for air-gapped/offline mode)."""

    async def lookup(self, ip: str) -> Optional[GeoInfo]:
        record_geoip_lookup("null", "miss")
        return None

    async def close(self) -> None:
        pass


def create_geoip_provider(
    settings: Settings, cache: GeoIPCacheRepository, session: Optional[aiohttp.ClientSession] = None
) -> GeoIpProvider:
    """Factory function to create the configured GeoIP provider."""
    provider_type = settings.geoip_provider

    if provider_type == "maxmind":
        if not settings.maxmind_db_path:
            logger.warning("MaxMind provider selected but no database path configured; falling back to NullProvider")
            return NullProvider()
        return MaxMindProvider(cache, settings)

    if provider_type == "ip-api":
        return IpApiProvider(cache, settings, session)

    logger.warning("Unknown geoip_provider '%s'; using NullProvider", provider_type)
    return NullProvider()