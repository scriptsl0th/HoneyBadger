"""Async SQLAlchemy storage layer with repositories.

Provides repositories for events, credentials, payloads, and GeoIP cache.
"""

import datetime as dt
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from metrics import record_db_events, record_db_up
from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import selectinload

from config import Settings
from db.models import Base, CredentialCount, Event, GeoIPCache, Payload
from schemas import EnrichedEvent, EventOut, GeoInfo, LoginInfo, Service, Severity

logger = logging.getLogger(__name__)


class Storage:
    """Main storage interface managing the database connection pool."""

    def __init__(self, database_url: str) -> None:
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._database_url = database_url

    async def init(self) -> None:
        """Initialize the engine and session factory."""
        self._engine = create_async_engine(
            self._database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        self._session_factory = async_sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        logger.info("Database storage initialized")

    async def close(self) -> None:
        """Close the engine and all connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database storage closed")

    async def update_event_count(self) -> None:
        """Update the total events gauge."""
        try:
            async with self.session() as session:
                result = await session.execute(select(func.count(Event.id)))
                count = result.scalar() or 0
                record_db_events(count)
        except Exception as e:
            logger.warning("Failed to update event count: %s", e)

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session."""
        if self._session_factory is None:
            raise RuntimeError("Storage not initialized. Call init() first.")
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @property
    def events(self) -> "EventRepository":
        return EventRepository(self)

    @property
    def credentials(self) -> "CredentialRepository":
        return CredentialRepository(self)

    @property
    def payloads(self) -> "PayloadRepository":
        return PayloadRepository(self)

    @property
    def geoip_cache(self) -> "GeoIPCacheRepository":
        return GeoIPCacheRepository(self)

    async def health_check(self) -> bool:
        """Check database connectivity and that the schema is migrated.

        A bare ``SELECT 1`` succeeds on an empty database, which used to make a
        schema-less backend report healthy while every real query returned 500.
        Touching ``events`` surfaces a missing/partial migration instead.
        """
        try:
            async with self.session() as session:
                await session.execute(select(Event.id).limit(1))
            record_db_up(True)
            return True
        except Exception as e:
            logger.error("Database health check failed: %s", e)
            record_db_up(False)
            return False


class EventRepository:
    """Repository for event persistence and queries."""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    async def insert(self, event: EnrichedEvent) -> None:
        """Insert an enriched event."""
        async with self._storage.session() as session:
            db_event = Event(
                ts=event.timestamp,
                service=event.service.value,
                source_ip=str(event.source_ip),
                destination_ip=str(event.destination_ip),
                source_port=event.source_port,
                destination_port=event.destination_port,
                username=event.login_info.username if event.login_info else None,
                password_hash=event.login_info.password_hash if event.login_info else None,
                user_agent=event.user_agent,
                http_method=event.http_method,
                http_path=event.http_path,
                http_status_code=event.http_status_code,
                command=event.command,
                payload_url=event.payload_url,
                payload_hash=event.payload_hash,
                payload_size=event.payload_size,
                technique_id=event.technique_id,
                severity=event.severity.value if event.severity else None,
                country=event.geo_info.country if event.geo_info else None,
                region=event.geo_info.region if event.geo_info else None,
                city=event.geo_info.city if event.geo_info else None,
                latitude=event.geo_info.latitude if event.geo_info else None,
                longitude=event.geo_info.longitude if event.geo_info else None,
                asn=event.geo_info.asn if event.geo_info else None,
                additional_info=event.additional_info,
            )
            session.add(db_event)

    async def query(
        self,
        *,
        limit: int = 50,
        service: Optional[str] = None,
        severity: Optional[str] = None,
        technique: Optional[str] = None,
        since: Optional[dt.datetime] = None,
        until: Optional[dt.datetime] = None,
    ) -> list[EventOut]:
        """Query events with filters, newest first."""
        async with self._storage.session() as session:
            stmt = select(Event).order_by(Event.ts.desc()).limit(limit)

            if service:
                stmt = stmt.where(Event.service == service)
            if severity:
                stmt = stmt.where(Event.severity == severity)
            if technique:
                stmt = stmt.where(Event.technique_id == technique)
            if since:
                stmt = stmt.where(Event.ts >= since)
            if until:
                stmt = stmt.where(Event.ts <= until)

            result = await session.execute(stmt)
            events = result.scalars().all()

            return [self._to_event_out(e) for e in events]

    async def stats(self, window: dt.timedelta) -> dict:
        """Get aggregated stats for a time window."""
        now = dt.datetime.now(dt.timezone.utc)
        start = now - window
        prev_start = start - window

        async with self._storage.session() as session:
            # Current window events
            current_stmt = select(Event).where(Event.ts >= start)
            current_result = await session.execute(current_stmt)
            current_events = current_result.scalars().all()

            # Previous window events (for comparison)
            prev_stmt = select(Event).where(Event.ts >= prev_start, Event.ts < start)
            prev_result = await session.execute(prev_stmt)
            prev_events = prev_result.scalars().all()

            return self._compute_stats(current_events, prev_events, window)

    async def timeseries(self, window: dt.timedelta, bucket_seconds: int) -> list[dict]:
        """Get time-series data for a window."""
        now = dt.datetime.now(dt.timezone.utc)
        start = now - window

        async with self._storage.session() as session:
            stmt = select(Event).where(Event.ts >= start).order_by(Event.ts)
            result = await session.execute(stmt)
            events = result.scalars().all()

        # Build buckets
        first_bucket = int(start.timestamp()) // bucket_seconds * bucket_seconds
        last_bucket = int(now.timestamp()) // bucket_seconds * bucket_seconds

        buckets: dict[int, dict] = {}
        cursor = first_bucket
        while cursor <= last_bucket:
            buckets[cursor] = {
                "ts": dt.datetime.fromtimestamp(cursor, dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                "total": 0,
                "ssh": 0,
                "http": 0,
                "low": 0,
                "medium": 0,
                "high": 0,
                "critical": 0,
            }
            cursor += bucket_seconds

        for event in events:
            epoch = int(event.ts.timestamp())
            key = epoch - epoch % bucket_seconds
            bucket = buckets.get(key)
            if bucket:
                bucket["total"] += 1
                bucket[event.service] += 1
                if event.severity:
                    bucket[event.severity] += 1

        return [buckets[key] for key in sorted(buckets)]

    def _to_event_out(self, event: Event) -> EventOut:
        """Convert DB Event to EventOut schema."""
        geo_info = None
        if any(
            [
                event.country,
                event.region,
                event.city,
                event.latitude is not None,
                event.longitude is not None,
                event.asn,
            ]
        ):
            geo_info = GeoInfo(
                country=event.country,
                region=event.region,
                city=event.city,
                latitude=event.latitude,
                longitude=event.longitude,
                asn=event.asn,
            )

        login_info = None
        if event.username or event.password_hash:
            login_info = LoginInfo(
                username=event.username,
                password_hash=event.password_hash,
            )

        return EventOut(
            service=Service(event.service),
            source_ip=event.source_ip,
            timestamp=event.ts,
            login_info=login_info,
            user_agent=event.user_agent,
            http_method=event.http_method,
            http_path=event.http_path,
            http_status_code=event.http_status_code,
            command=event.command,
            payload_url=event.payload_url,
            payload_hash=event.payload_hash,
            payload_size=event.payload_size,
            geo_info=geo_info,
            technique_id=event.technique_id,
            severity=Severity(event.severity) if event.severity else None,
        )

    def _compute_stats(
        self, current: list[Event], previous: list[Event], window: dt.timedelta
    ) -> dict:
        """Compute stats from event lists."""
        from collections import Counter

        credentials: dict[tuple[str, str], list] = {}
        sources: dict[str, dict] = {}
        paths: Counter[str] = Counter()
        payloads: dict[str, dict] = {}

        for event in current:
            if event.username and event.password_hash:
                key = (event.username, event.password_hash)
                entry = credentials.setdefault(key, [0, event.ts])
                entry[0] += 1
                entry[1] = max(entry[1], event.ts)

            ip = str(event.source_ip)
            source = sources.setdefault(
                ip,
                {
                    "source_ip": ip,
                    "country": event.country,
                    "city": event.city,
                    "latitude": event.latitude,
                    "longitude": event.longitude,
                    "asn": event.asn,
                    "count": 0,
                    "last_seen": event.ts,
                },
            )
            source["count"] += 1
            source["last_seen"] = max(source["last_seen"], event.ts)
            if event.country:
                source["country"] = source["country"] or event.country
            if event.city:
                source["city"] = source["city"] or event.city
            if event.latitude is not None:
                source["latitude"] = source["latitude"] or event.latitude
            if event.longitude is not None:
                source["longitude"] = source["longitude"] or event.longitude
            if event.asn:
                source["asn"] = source["asn"] or event.asn

            if event.http_path:
                paths[event.http_path] += 1

            if event.payload_url:
                payload = payloads.setdefault(
                    event.payload_url,
                    {
                        "url": event.payload_url,
                        "hash": event.payload_hash,
                        "size": event.payload_size,
                        "quarantined": False,
                        "first_seen": event.ts,
                    },
                )
                payload["hash"] = payload["hash"] or event.payload_hash
                payload["size"] = (
                    payload["size"] if payload["size"] is not None else event.payload_size
                )
                payload["first_seen"] = min(payload["first_seen"], event.ts)

        def _iso(value: dt.datetime) -> str:
            return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")

        top_credentials = [
            {
                "username": username,
                "password_hash": password_hash,
                "count": count,
                "last_seen": _iso(last_seen),
            }
            for (username, password_hash), (count, last_seen) in sorted(
                credentials.items(), key=lambda item: (-item[1][0], item[0])
            )[:10]
        ]

        top_sources = sorted(
            sources.values(), key=lambda item: (-item["count"], item["source_ip"])
        )[:10]
        for source in top_sources:
            source["last_seen"] = _iso(source["last_seen"])

        return {
            "window": str(window),
            "generated_at": _iso(dt.datetime.now(dt.timezone.utc)),
            "totals": {
                "events": len(current),
                "events_previous": len(previous),
                "events_per_minute": round(
                    len(current) / max(1.0, window.total_seconds() / 60)
                ),
                "unique_sources": len({str(e.source_ip) for e in current}),
                "unique_credentials": len(credentials),
                "payloads": len(payloads),
                "high_or_critical": sum(
                    1 for e in current if e.severity in ("high", "critical")
                ),
            },
            "by_service": [
                {"service": s, "count": c}
                for s, c in Counter(e.service for e in current).most_common()
            ],
            "by_severity": [
                {"severity": s, "count": c}
                for s, c in Counter(e.severity for e in current if e.severity).most_common()
            ],
            "by_technique": [
                {"technique_id": t, "count": c}
                for t, c in Counter(e.technique_id for e in current if e.technique_id).most_common()
            ],
            "top_credentials": top_credentials,
            "top_sources": top_sources,
            "top_paths": [
                {"http_path": p, "count": c} for p, c in paths.most_common(10)
            ],
            "payloads": [
                {**p, "first_seen": _iso(p["first_seen"])}
                for p in sorted(payloads.values(), key=lambda x: x["first_seen"], reverse=True)[:10]
            ],
        }


class CredentialRepository:
    """Repository for credential count aggregates."""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    async def increment(self, username: str, password_hash: str) -> None:
        """Increment or insert a credential pair counter."""
        async with self._storage.session() as session:
            stmt = (
                pg_insert(CredentialCount)
                .values(username=username, password_hash=password_hash, count=1)
                .on_conflict_do_update(
                    index_elements=["username", "password_hash"],
                    set_={
                        "count": CredentialCount.count + 1,
                        "last_seen": func.now(),
                    },
                )
            )
            await session.execute(stmt)

    async def top_n(self, n: int = 10) -> list[dict]:
        """Get top N credential pairs by count."""
        async with self._storage.session() as session:
            stmt = (
                select(CredentialCount)
                .order_by(CredentialCount.count.desc(), CredentialCount.last_seen.desc())
                .limit(n)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

            return [
                {
                    "username": r.username,
                    "password_hash": r.password_hash,
                    "count": r.count,
                    "last_seen": r.last_seen.isoformat().replace("+00:00", "Z"),
                }
                for r in rows
            ]


class PayloadRepository:
    """Repository for payload metadata."""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    async def upsert(
        self, url: str, hash_: Optional[str] = None, size: Optional[int] = None
    ) -> None:
        """Insert or update payload metadata."""
        async with self._storage.session() as session:
            stmt = (
                pg_insert(Payload)
                .values(url=url, hash=hash_, size=size)
                .on_conflict_do_update(
                    index_elements=["url"],
                    set_={
                        "hash": hash_ if hash_ else Payload.hash,
                        "size": size if size is not None else Payload.size,
                        "last_seen": func.now(),
                    },
                )
            )
            await session.execute(stmt)

    async def mark_quarantined(self, url: str, quarantine_path: str) -> None:
        """Mark a payload as quarantined with its storage path."""
        async with self._storage.session() as session:
            stmt = (
                update(Payload)
                .where(Payload.url == url)
                .values(quarantined=True, quarantine_path=quarantine_path)
            )
            await session.execute(stmt)

    async def get_quarantined(self) -> list[dict]:
        """Get all quarantined payloads."""
        async with self._storage.session() as session:
            stmt = select(Payload).where(Payload.quarantined == True)
            result = await session.execute(stmt)
            rows = result.scalars().all()

            return [
                {
                    "url": r.url,
                    "hash": r.hash,
                    "size": r.size,
                    "quarantine_path": r.quarantine_path,
                    "first_seen": r.first_seen.isoformat().replace("+00:00", "Z"),
                }
                for r in rows
            ]


class GeoIPCacheRepository:
    """Repository for GeoIP cache with TTL."""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    async def get(self, ip: str) -> Optional[GeoInfo]:
        """Get cached GeoIP info if not expired."""
        async with self._storage.session() as session:
            stmt = select(GeoIPCache).where(
                GeoIPCache.ip == ip, GeoIPCache.expires_at > func.now()
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()

            if row:
                return GeoInfo(
                    country=row.country,
                    region=row.region,
                    city=row.city,
                    latitude=row.latitude,
                    longitude=row.longitude,
                    asn=row.asn,
                )
            return None

    async def set(self, ip: str, info: GeoInfo, ttl_days: int) -> None:
        """Set GeoIP cache entry with TTL."""
        expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=ttl_days)

        async with self._storage.session() as session:
            stmt = (
                pg_insert(GeoIPCache)
                .values(
                    ip=ip,
                    country=info.country,
                    region=info.region,
                    city=info.city,
                    latitude=info.latitude,
                    longitude=info.longitude,
                    asn=info.asn,
                    expires_at=expires_at,
                )
                .on_conflict_do_update(
                    index_elements=["ip"],
                    set_={
                        "country": info.country,
                        "region": info.region,
                        "city": info.city,
                        "latitude": info.latitude,
                        "longitude": info.longitude,
                        "asn": info.asn,
                        "expires_at": expires_at,
                    },
                )
            )
            await session.execute(stmt)

    async def purge_expired(self) -> int:
        """Delete expired cache entries. Returns count of deleted rows."""
        async with self._storage.session() as session:
            stmt = delete(GeoIPCache).where(GeoIPCache.expires_at <= func.now())
            result = await session.execute(stmt)
            return result.rowcount