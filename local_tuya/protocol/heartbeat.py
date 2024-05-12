import logging

from concurrent_tasks import PeriodicTask

from local_tuya.errors import CommandTimeoutError
from local_tuya.events import EventNotifier
from local_tuya.protocol.events import (
    CommandSent,
    ConnectionClosed,
    ConnectionEstablished,
)
from local_tuya.protocol.message import HeartbeatCommand

logger = logging.getLogger(__name__)


class Heartbeat(PeriodicTask):
    def __init__(self, interval: float, event_notifier: EventNotifier):
        super().__init__(interval, _heartbeat, event_notifier)
        event_notifier.register(ConnectionClosed, lambda _: self.cancel())
        event_notifier.register(ConnectionEstablished, lambda _: self.create())

    def __enter__(self) -> "Heartbeat":
        """Don't start automatically, only when connection is established."""
        return self


async def _heartbeat(event_notifier: EventNotifier) -> None:
    try:
        await event_notifier.emit(CommandSent(HeartbeatCommand()))
    except CommandTimeoutError:
        logger.warning("timeout waiting for heartbeat response")
