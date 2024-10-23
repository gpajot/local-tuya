import logging

from concurrent_tasks import PeriodicTask

from local_tuya.errors import CommandTimeoutError
from local_tuya.events import EventNotifier
from local_tuya.tuya.events import (
    TuyaCommandSent,
    TuyaConnectionClosed,
    TuyaConnectionEstablished,
)
from local_tuya.tuya.message import HeartbeatCommand

logger = logging.getLogger(__name__)


class Heartbeat(PeriodicTask):
    def __init__(self, name: str, interval: float, event_notifier: EventNotifier):
        super().__init__(interval, _heartbeat, name, event_notifier)
        event_notifier.register(TuyaConnectionClosed, lambda _: self.cancel())
        event_notifier.register(TuyaConnectionEstablished, lambda _: self.create())
        self._name = name

    def __enter__(self) -> "Heartbeat":
        """Don't start automatically, only when connection is established."""
        return self


async def _heartbeat(name: str, event_notifier: EventNotifier) -> None:
    try:
        await event_notifier.emit(TuyaCommandSent(HeartbeatCommand()))
    except CommandTimeoutError:
        logger.warning("%s: timeout waiting for heartbeat response", name)
