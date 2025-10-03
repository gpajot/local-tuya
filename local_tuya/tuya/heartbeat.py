from typing import Self

from concurrent_tasks import PeriodicTask

from local_tuya.events import EventNotifier
from local_tuya.tuya.events import (
    TuyaCommandSent,
    TuyaConnectionClosed,
    TuyaConnectionEstablished,
)
from local_tuya.tuya.message import HeartbeatCommand


class Heartbeat(PeriodicTask):
    def __init__(self, interval: float, event_notifier: EventNotifier):
        super().__init__(interval, self._heartbeat)
        self._notifier = event_notifier
        event_notifier.register(TuyaConnectionClosed, lambda _: self.cancel())
        event_notifier.register(TuyaConnectionEstablished, lambda _: self.create())

    def __enter__(self) -> Self:
        """Don't start automatically, only when connection is established."""
        return self

    async def _heartbeat(self) -> None:
        await self._notifier.emit(TuyaCommandSent(HeartbeatCommand()))
