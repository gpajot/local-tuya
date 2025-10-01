import logging
from typing import Self

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
        super().__init__(interval, self._heartbeat)
        event_notifier.register(TuyaConnectionClosed, lambda _: self.cancel())
        event_notifier.register(TuyaConnectionEstablished, lambda _: self.create())
        self._name = name
        self._notifier = event_notifier

    def __enter__(self) -> Self:
        """Don't start automatically, only when connection is established."""
        return self

    async def _heartbeat(self) -> None:
        try:
            await self._notifier.emit(TuyaCommandSent(HeartbeatCommand()))
        except CommandTimeoutError:
            logger.debug("%s: timeout waiting for heartbeat response", self._name)
