"""Read-only REST + WebSocket bridge for the dashboard.

This is the in-memory preview of slice 4: it implements the shapes in
``docs/API.md`` so the React dashboard can be exercised against the real SSH
honeypot today. Events live in RAM (a restart clears the feed); PostgreSQL,
GeoIP and ATT&CK enrichment arrive with slices 3 and 4.

Only ``auth``/``command`` events become dashboard rows. SSH handshake banners
are connection telemetry, not attacker actions, so they stay off the feed.
"""

import asyncio
import datetime as dt
import json
import time
import typing as t
from collections import Counter, deque

from aiohttp import WSMsgType, web

from config import Settings
from schemas import (
    SSH_HANDSHAKE_KIND,
    EventOut,
    RawEvent,
    Service,
    Severity,
)

VERSION = "0.1.0"

# window -> (duration, bucket size in seconds)
WINDOWS: dict[str, tuple[dt.timedelta, int]] = {
    "15m": (dt.timedelta(minutes=15), 30),
    "1h": (dt.timedelta(hours=1), 60),
    "6h": (dt.timedelta(hours=6), 300),
    "24h": (dt.timedelta(hours=24), 900),
    "7d": (dt.timedelta(days=7), 3600),
}

TECHNIQUES = {
    "T1110",
    "T1110.004",
    "T1595",
    "T1190",
    "T1105",
    "T1059",
    "T1078",
}

TOP_N = 10


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> dt.datetime | None:
    try:
        parsed = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(dt.timezone.utc)


def _bad(detail: str) -> web.Response:
    return web.json_response(
        {"error": "invalid_request", "detail": detail}, status=400
    )


class EventStore:
    """Bounded in-memory event log with live WebSocket fan-out."""

    def __init__(self, capacity: int = 10_000) -> None:
        self._events: deque[EventOut] = deque(maxlen=capacity)
        self._sockets: set[web.WebSocketResponse] = set()
        self._tasks: set[asyncio.Task[None]] = set()
        self._started = time.monotonic()

    # -- ingestion --------------------------------------------------------

    async def record(self, raw: RawEvent) -> None:
        """Bus listener: keep the event, then push it to live clients."""
        if raw.additional_info is not None:
            if raw.additional_info.get("event_kind") == SSH_HANDSHAKE_KIND:
                return

        event = EventOut(
            service=raw.service,
            source_ip=raw.source_ip,
            timestamp=raw.timestamp,
            login_info=raw.login_info,
            user_agent=raw.user_agent,
            http_method=raw.http_method,
            http_path=raw.http_path,
            http_status_code=raw.http_status_code,
            command=raw.command,
            payload_url=raw.payload_url,
            payload_hash=raw.payload_hash,
            payload_size=raw.payload_size,
        )
        self._events.append(event)

        if self._sockets:
            message = {"type": "event", "event": event.model_dump(mode="json")}
            for socket in list(self._sockets):
                if socket.closed:
                    self._sockets.discard(socket)
                    continue
                task = asyncio.create_task(self._send(socket, message))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)

    async def _send(
        self, socket: web.WebSocketResponse, message: dict[str, t.Any]
    ) -> None:
        try:
            await socket.send_json(message)
        except (ConnectionError, RuntimeError):
            self._sockets.discard(socket)

    # -- WebSocket bookkeeping -------------------------------------------

    def register(self, socket: web.WebSocketResponse) -> None:
        self._sockets.add(socket)

    def unregister(self, socket: web.WebSocketResponse) -> None:
        self._sockets.discard(socket)

    async def close(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    # -- queries ----------------------------------------------------------

    @property
    def uptime_s(self) -> int:
        return int(time.monotonic() - self._started)

    def query(
        self,
        *,
        limit: int = 50,
        service: str | None = None,
        severity: str | None = None,
        technique: str | None = None,
        since: dt.datetime | None = None,
        until: dt.datetime | None = None,
    ) -> list[EventOut]:
        """Newest first, with the filters from ``docs/API.md`` section 4."""
        items: list[EventOut] = []
        for event in reversed(self._events):
            if service is not None and event.service.value != service:
                continue
            if (
                severity is not None
                and (event.severity is None or event.severity.value != severity)
            ):
                continue
            if technique is not None and event.technique_id != technique:
                continue
            if since is not None and event.timestamp < since:
                continue
            if until is not None and event.timestamp > until:
                continue
            items.append(event)
            if len(items) >= limit:
                break
        return items

    def stats(self, window: str) -> dict[str, t.Any]:
        now = _now()
        delta = WINDOWS[window][0]
        start = now - delta
        current = [
            event for event in self._events if start <= event.timestamp <= now
        ]
        previous = [
            event
            for event in self._events
            if start - delta <= event.timestamp < start
        ]

        credentials: dict[tuple[str, str], list[t.Any]] = {}
        sources: dict[str, dict[str, t.Any]] = {}
        paths: Counter[str] = Counter()
        payloads: dict[str, dict[str, t.Any]] = {}

        for event in current:
            if event.login_info is not None:
                username = event.login_info.username
                password_hash = event.login_info.password_hash
                if username and password_hash:
                    key = (username, password_hash)
                    entry = credentials.setdefault(
                        key, [0, event.timestamp]
                    )
                    entry[0] += 1
                    entry[1] = max(entry[1], event.timestamp)

            ip = str(event.source_ip)
            source = sources.setdefault(
                ip,
                {
                    "source_ip": ip,
                    "country": None,
                    "city": None,
                    "latitude": None,
                    "longitude": None,
                    "asn": None,
                    "count": 0,
                    "last_seen": event.timestamp,
                },
            )
            source["count"] += 1
            source["last_seen"] = max(source["last_seen"], event.timestamp)
            if event.geo_info is not None:
                source["country"] = source["country"] or event.geo_info.country
                source["city"] = source["city"] or event.geo_info.city
                source["latitude"] = (
                    source["latitude"]
                    if source["latitude"] is not None
                    else event.geo_info.latitude
                )
                source["longitude"] = (
                    source["longitude"]
                    if source["longitude"] is not None
                    else event.geo_info.longitude
                )
                source["asn"] = source["asn"] or event.geo_info.asn

            if event.http_path:
                paths[event.http_path] += 1

            if event.payload_url:
                payload = payloads.setdefault(
                    event.payload_url,
                    {
                        "url": event.payload_url,
                        "hash": None,
                        "size": None,
                        "quarantined": False,
                        "first_seen": event.timestamp,
                    },
                )
                payload["hash"] = payload["hash"] or event.payload_hash
                payload["size"] = (
                    payload["size"]
                    if payload["size"] is not None
                    else event.payload_size
                )
                payload["first_seen"] = min(
                    payload["first_seen"], event.timestamp
                )

        top_credentials = [
            {
                "username": username,
                "password_hash": password_hash,
                "count": count,
                "last_seen": _iso(last_seen),
            }
            for (username, password_hash), (count, last_seen) in sorted(
                credentials.items(), key=lambda item: (-item[1][0], item[0])
            )[:TOP_N]
        ]

        top_sources = sorted(
            sources.values(), key=lambda item: (-item["count"], item["source_ip"])
        )[:TOP_N]
        for source in top_sources:
            source["last_seen"] = _iso(source["last_seen"])

        return {
            "window": window,
            "generated_at": _iso(now),
            "totals": {
                "events": len(current),
                "events_previous": len(previous),
                "events_per_minute": round(
                    len(current) / max(1.0, delta.total_seconds() / 60)
                ),
                "unique_sources": len({str(event.source_ip) for event in current}),
                "unique_credentials": len(credentials),
                "payloads": len(payloads),
                "high_or_critical": sum(
                    1
                    for event in current
                    if event.severity in (Severity.HIGH, Severity.CRITICAL)
                ),
            },
            "by_service": [
                {"service": service.value, "count": count}
                for service, count in Counter(
                    event.service for event in current
                ).most_common()
            ],
            "by_severity": [
                {"severity": severity.value, "count": count}
                for severity, count in Counter(
                    event.severity
                    for event in current
                    if event.severity is not None
                ).most_common()
            ],
            "by_technique": [
                {"technique_id": technique, "count": count}
                for technique, count in Counter(
                    event.technique_id
                    for event in current
                    if event.technique_id is not None
                ).most_common()
            ],
            "top_credentials": top_credentials,
            "top_sources": top_sources,
            "top_paths": [
                {"http_path": path, "count": count}
                for path, count in paths.most_common(TOP_N)
            ],
            "payloads": [
                {**payload, "first_seen": _iso(payload["first_seen"])}
                for payload in sorted(
                    payloads.values(),
                    key=lambda item: item["first_seen"],
                    reverse=True,
                )[:TOP_N]
            ],
        }

    def timeseries(self, window: str) -> dict[str, t.Any]:
        delta, bucket_seconds = WINDOWS[window]
        now = _now()
        first = int((now - delta).timestamp()) // bucket_seconds * bucket_seconds
        last = int(now.timestamp()) // bucket_seconds * bucket_seconds

        buckets: dict[int, dict[str, t.Any]] = {}
        cursor = first
        while cursor <= last:
            buckets[cursor] = {
                "ts": _iso(dt.datetime.fromtimestamp(cursor, dt.timezone.utc)),
                "total": 0,
                "ssh": 0,
                "http": 0,
                "low": 0,
                "medium": 0,
                "high": 0,
                "critical": 0,
            }
            cursor += bucket_seconds

        for event in self._events:
            epoch = int(event.timestamp.timestamp())
            key = epoch - epoch % bucket_seconds
            point = buckets.get(key)
            if point is None:
                continue
            point["total"] += 1
            point[event.service.value] += 1
            if event.severity is not None:
                point[event.severity.value] += 1

        return {
            "window": window,
            "bucket_seconds": bucket_seconds,
            "points": [buckets[key] for key in sorted(buckets)],
        }


# -- HTTP handlers ---------------------------------------------------------


STORE_KEY: web.AppKey[EventStore] = web.AppKey("store", EventStore)


def _store(request: web.Request) -> EventStore:
    return request.app[STORE_KEY]


async def _health(request: web.Request) -> web.Response:
    store = _store(request)
    return web.json_response(
        {
            "status": "ok",
            "db": "ok",
            "version": VERSION,
            "uptime_s": store.uptime_s,
        }
    )


async def _events(request: web.Request) -> web.Response:
    store = _store(request)

    raw_limit = request.query.get("limit", "50")
    try:
        limit = int(raw_limit)
    except ValueError:
        return _bad("limit must be an integer")
    if not 1 <= limit <= 500:
        return _bad("limit must be between 1 and 500")

    service = request.query.get("service")
    if service is not None and service not in {item.value for item in Service}:
        return _bad("service must be 'ssh' or 'http'")

    severity = request.query.get("severity")
    if severity is not None and severity not in {item.value for item in Severity}:
        return _bad("severity is not a known level")

    technique = request.query.get("technique")
    if technique is not None and technique not in TECHNIQUES:
        return _bad("technique is not a known ATT&CK technique")

    since = None
    if "since" in request.query:
        since = _parse_timestamp(request.query["since"])
        if since is None:
            return _bad("since must be an RFC 3339 timestamp")

    until = None
    if "until" in request.query:
        until = _parse_timestamp(request.query["until"])
        if until is None:
            return _bad("until must be an RFC 3339 timestamp")

    items = store.query(
        limit=limit,
        service=service,
        severity=severity,
        technique=technique,
        since=since,
        until=until,
    )
    return web.json_response(
        {"items": [event.model_dump(mode="json") for event in items]}
    )


def _window(request: web.Request) -> tuple[str | None, web.Response | None]:
    window = request.query.get("window", "1h")
    if window not in WINDOWS:
        return None, _bad("window must be one of: 15m, 1h, 6h, 24h, 7d")
    return window, None


async def _stats(request: web.Request) -> t.Any:
    window, error = _window(request)
    if error is not None:
        return error
    assert window is not None
    return web.json_response(_store(request).stats(window))


async def _timeseries(request: web.Request) -> t.Any:
    window, error = _window(request)
    if error is not None:
        return error
    assert window is not None
    return web.json_response(_store(request).timeseries(window))


async def _websocket(request: web.Request) -> web.WebSocketResponse:
    store = _store(request)
    socket = web.WebSocketResponse(heartbeat=30)
    await socket.prepare(request)
    store.register(socket)
    try:
        await socket.send_json({"type": "hello", "server_time": _iso(_now())})
        async for message in socket:
            if message.type is not WSMsgType.TEXT:
                continue
            try:
                payload = json.loads(message.data)
            except ValueError:
                continue
            if isinstance(payload, dict) and payload.get("type") == "ping":
                await socket.send_json(
                    {"type": "pong", "server_time": _iso(_now())}
                )
    finally:
        store.unregister(socket)
    return socket


def create_app(store: EventStore | None = None) -> web.Application:
    store = store or EventStore()
    app = web.Application()
    app[STORE_KEY] = store
    app.router.add_get("/health", _health)
    app.router.add_get("/events", _events)
    app.router.add_get("/stats", _stats)
    app.router.add_get("/stats/timeseries", _timeseries)
    app.router.add_get("/ws/events", _websocket)

    async def cleanup(_: web.Application) -> None:
        await store.close()

    app.on_cleanup.append(cleanup)
    return app


async def start_api_server(
    settings: Settings, store: EventStore
) -> web.AppRunner:
    """Bind the REST/WebSocket server; caller owns shutdown via cleanup()."""
    runner = web.AppRunner(create_app(store))
    await runner.setup()
    site = web.TCPSite(runner, settings.api_host, settings.api_port)
    await site.start()
    return runner
