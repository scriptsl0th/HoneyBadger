import asyncio

import pytest

from bus import EventBus


def _run(coro):
    return asyncio.run(coro)


def test_delivers_to_single_listener():
    async def scenario():
        bus = EventBus("test")
        received = []

        async def listener(event):
            received.append(event)

        bus.subscribe(listener)
        await bus.start()
        bus.publish("evt")
        await bus.stop()
        return received

    assert _run(scenario()) == ["evt"]


def test_fans_out_to_all_listeners_in_order():
    async def scenario():
        bus = EventBus("test")
        first, second = [], []

        async def listener_a(event):
            first.append(event)

        async def listener_b(event):
            second.append(event)

        bus.subscribe(listener_a)
        bus.subscribe(listener_b)
        await bus.start()
        for i in range(5):
            bus.publish(f"e-{i}")
        await bus.stop()
        return first, second

    expected = [f"e-{i}" for i in range(5)]
    first, second = _run(scenario())
    assert first == expected
    assert second == expected


def test_listener_failure_does_not_stop_delivery(caplog):
    async def scenario():
        bus = EventBus("test")
        received = []

        async def bad_listener(event):
            raise ValueError("kaboom")

        async def good_listener(event):
            received.append(event)

        bus.subscribe(bad_listener)
        bus.subscribe(good_listener)
        await bus.start()
        bus.publish("a")
        bus.publish("b")
        await bus.stop()
        return received

    assert _run(scenario()) == ["a", "b"]
    assert "listener failed" in caplog.text


def test_sync_raising_listener_does_not_kill_consumer(caplog):
    async def scenario():
        bus = EventBus("test")
        received = []

        def bad_sync_listener(event):
            raise ValueError("sync kaboom")

        async def good_listener(event):
            received.append(event)

        bus.subscribe(bad_sync_listener)
        bus.subscribe(good_listener)
        await bus.start()
        bus.publish("a")
        bus.publish("b")
        await bus.stop()
        return received

    assert _run(scenario()) == ["a", "b"]
    assert "listener failed" in caplog.text


def test_no_replay_for_events_published_before_subscription():
    async def scenario():
        bus = EventBus("test")
        received = []

        async def listener(event):
            received.append(event)

        bus.publish("before")
        bus.subscribe(listener)
        bus.publish("after")
        await bus.start()
        await bus.stop()
        return received

    assert _run(scenario()) == ["after"]


def test_subscribe_after_start_raises():
    async def scenario():
        bus = EventBus("test")

        async def listener(event):
            pass

        await bus.start()
        with pytest.raises(RuntimeError):
            bus.subscribe(listener)
        await bus.stop()

    _run(scenario())


def test_stop_without_start_is_noop():
    async def scenario():
        bus = EventBus("test")

        async def listener(event):
            pass

        bus.subscribe(listener)
        await bus.stop()

    _run(scenario())