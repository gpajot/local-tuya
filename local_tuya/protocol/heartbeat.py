import asyncio
import logging

from concurrent_tasks import BackgroundTask

from local_tuya.errors import CommandTimeoutError
from local_tuya.events import EventNotifier
from local_tuya.protocol.events import (
    CommandSent,
    ConnectionEstablished,
    ConnectionLost,
)
from local_tuya.protocol.message import HeartbeatCommand

logger = logging.getLogger(__name__)


class Heartbeat(BackgroundTask):
    def __init__(self, interval: float, event_notifier: EventNotifier):
        super().__init__(self._run, interval, event_notifier)
        event_notifier.register(ConnectionLost, lambda _: self.cancel())
        event_notifier.register(ConnectionEstablished, lambda _: self.create())

    def __enter__(self) -> "Heartbeat":
        return self

    async def _run(self, interval: float, event_notifier: EventNotifier) -> None:
        while True:
            try:
                await event_notifier.emit(CommandSent(HeartbeatCommand()))
            except CommandTimeoutError:
                logger.warning("timeout waiting for heartbeat response")
            await asyncio.sleep(interval)
