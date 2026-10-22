import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

logger = logging.getLogger(__name__)

EventT = TypeVar("EventT")
ListenerT = Callable[[EventT], Awaitable[None]]


class _Sentinel:
    """Marker enqueued by stop() to drain the queue and end the consumer."""


class EventBus(Generic[EventT]):
    """In-process event bus with concurrent fan-out.

    Each published event is delivered concurrently to the listeners that
    were subscribed when it was enqueued. A slow or failing listener never
    blocks the producers or the other listeners.
    """

    _SENTINEL = _Sentinel()
    STOP_TIMEOUT = 30

    def __init__(self, name: str = "default") -> None:
        self.name = name
        self.listeners: list[ListenerT] = []
        self._queue: asyncio.Queue[
            tuple[EventT, list[ListenerT]] | _Sentinel
        ] = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self.started = False

    def subscribe(self, listener: ListenerT) -> None:
        """Register a listener. Listeners must be added before start()."""
        if self.started:
            raise RuntimeError(f"cannot subscribe to started bus '{self.name}'")
        self.listeners.append(listener)
        logger.debug("listener %s subscribed to %s bus", listener, self.name)

    def publish(self, event: EventT) -> None:
        """Enqueue an event for delivery. Never blocks the caller."""
        self._queue.put_nowait((event, list(self.listeners)))
        logger.debug("event '%s' published to %s bus", event, self.name)

    async def start(self) -> None:
        if self.started:
            logger.warning("bus %s already started", self.name)
            return
        self.started = True
        self._task = asyncio.create_task(
            self._consume(), name=f"{self.name}-event-bus-consumer"
        )
        logger.info("bus %s started", self.name)

    async def stop(self) -> None:
        if not self.started:
            logger.warning("bus %s not started", self.name)
            return
        self.started = False
        await self._queue.put(self._SENTINEL)
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=self.STOP_TIMEOUT)
            except TimeoutError:
                self._task.cancel()
                logger.warning("bus %s consumer hit stop timeout; cancelled", self.name)
        self._task = None
        logger.info("bus %s stopped", self.name)

    async def _consume(self) -> None:
        while True:
            item = await self._queue.get()
            if isinstance(item, _Sentinel):
                break
            event, listeners = item
            await self._dispatch(event, listeners)

    async def _dispatch(self, event: EventT, listeners: list[ListenerT]) -> None:
        results = await asyncio.gather(
            *(self._invoke(listener, event) for listener in listeners),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, BaseException) and not isinstance(
                result, asyncio.CancelledError
            ):
                logger.exception(
                    "listener failed on %s event '%s'", self.name, event, exc_info=result
                )

    @staticmethod
    async def _invoke(listener: ListenerT, event: EventT) -> None:
        """Run one listener; keeps a synchronous failure isolated per listener."""
        await listener(event)