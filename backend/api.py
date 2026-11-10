"""Read-only REST + WebSocket bridge for the dashboard.

Uses enriched events from the pipeline and queries PostgreSQL via storage repositories.
"""

import asyncio
import datetime as dt
import json
import time
import typing as t
from collections import Counter

from aiohttp import WSMsgType, web

from bus import EventBus
from config import Settings
from metrics import (
    record_api_latency,
    record_api_request,
    record_ws_connections,
)
from schemas import (
    EnrichedEvent,
    EventOut,
    Service,
    Severity,
)
from storage import Storage

VERSION = "0.2.0"

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


class EnrichedEventStore:
    """Consumes enriched events from bus and provides WebSocket fan-out."""

    def __init__(self, enriched_bus: EventBus[EnrichedEvent], storage: Storage) -> None:
        self._enriched_bus = enriched_bus
        self._storage = storage
        self._sockets: set[web.WebSocketResponse] = set()
        self._tasks: set[asyncio.Task[None]] = set()
        self._started = time.monotonic()

    async def start(self) -> None:
        """Subscribe to enriched bus."""
        self._enriched_bus.subscribe(self._on_enriched_event)
        await self._enriched_bus.start()

    async def stop(self) -> None:
        """Stop consuming and close connections."""
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        await self._enriched_bus.stop()

    async def _on_enriched_event(self, event: EnrichedEvent) -> None:
        """Handle enriched event from pipeline - broadcast to WebSocket clients."""
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

    def register(self, socket: web.WebSocketResponse) -> None:
        self._sockets.add(socket)
        record_ws_connections(len(self._sockets))

    def unregister(self, socket: web.WebSocketResponse) -> None:
        self._sockets.discard(socket)
        record_ws_connections(len(self._sockets))

    @property
    def uptime_s(self) -> int:
        return int(time.monotonic() - self._started)


STORE_KEY: web.AppKey[EnrichedEventStore] = web.AppKey("store", EnrichedEventStore)
STORAGE_KEY: web.AppKey[Storage] = web.AppKey("storage", Storage)


def _store(request: web.Request) -> EnrichedEventStore:
    return request.app[STORE_KEY]


def _storage(request: web.Request) -> Storage:
    return request.app[STORAGE_KEY]


async def _health(request: web.Request) -> web.Response:
    store = _store(request)
    storage = _storage(request)
    db_ok = await storage.health_check()
    return web.json_response(
        {
            "status": "ok" if db_ok else "degraded",
            "db": "ok" if db_ok else "error",
            "version": VERSION,
            "uptime_s": store.uptime_s,
        },
        status=200 if db_ok else 503,
    )


async def _events(request: web.Request) -> web.Response:
    store = _store(request)
    storage = _storage(request)

    start_time = time.time()

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

    # Query from PostgreSQL
    items = await storage.events.query(
        limit=limit,
        service=service,
        severity=severity,
        technique=technique,
        since=since,
        until=until,
    )

    record_api_request("/events", request.method, 200)
    record_api_latency("/events", time.time() - start_time)

    return web.json_response(
        {"items": [event.model_dump(mode="json") for event in items]}
    )


def _window(request: web.Request) -> tuple[str | None, web.Response | None]:
    window = request.query.get("window", "1h")
    if window not in WINDOWS:
        return None, _bad("window must be one of: 15m, 1h, 6h, 24h, 7d")
    return window, None


async def _stats(request: web.Request) -> t.Any:
    start_time = time.time()
    window, error = _window(request)
    if error is not None:
        return error
    assert window is not None

    storage = _storage(request)
    delta = WINDOWS[window][0]
    stats = await storage.events.stats(delta)

    record_api_request("/stats", request.method, 200)
    record_api_latency("/stats", time.time() - start_time)

    return web.json_response(stats)


async def _timeseries(request: web.Request) -> t.Any:
    start_time = time.time()
    window, error = _window(request)
    if error is not None:
        return error
    assert window is not None

    storage = _storage(request)
    delta, bucket_seconds = WINDOWS[window]
    timeseries = await storage.events.timeseries(delta, bucket_seconds)

    record_api_request("/stats/timeseries", request.method, 200)
    record_api_latency("/stats/timeseries", time.time() - start_time)

    return web.json_response(timeseries)


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


def create_app(
    enriched_bus: EventBus[EnrichedEvent] | None = None,
    storage: Storage | None = None,
) -> web.Application:
    if enriched_bus is None or storage is None:
        raise ValueError("enriched_bus and storage are required")

    store = EnrichedEventStore(enriched_bus, storage)
    app = web.Application()
    app[STORE_KEY] = store
    app[STORAGE_KEY] = storage
    app.router.add_get("/health", _health)
    app.router.add_get("/events", _events)
    app.router.add_get("/stats", _stats)
    app.router.add_get("/stats/timeseries", _timeseries)
    app.router.add_get("/ws/events", _websocket)

    async def on_startup(app: web.Application) -> None:
        await store.start()

    async def on_cleanup(app: web.Application) -> None:
        await store.stop()

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


async def start_api_server(
    settings: Settings,
    enriched_bus: EventBus[EnrichedEvent],
    storage: Storage,
) -> web.AppRunner:
    """Bind the REST/WebSocket server; caller owns shutdown via cleanup()."""
    app = create_app(enriched_bus, storage)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.api_host, settings.api_port)
    await site.start()
    return runner