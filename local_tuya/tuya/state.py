import logging

from concurrent_tasks import PeriodicTask
from typing_extensions import Optional

from local_tuya.errors import CommandTimeoutError
from local_tuya.events import EventNotifier
from local_tuya.protocol import Values
from local_tuya.tuya.events import (
    TuyaCommandSent,
    TuyaConnectionClosed,
    TuyaConnectionEstablished,
    TuyaResponseReceived,
    TuyaStateUpdated,
)
from local_tuya.tuya.message import (
    StateCommand,
    StateResponse,
    StatusResponse,
)

logger = logging.getLogger(__name__)


class State(PeriodicTask):
    def __init__(
        self,
        name: str,
        refresh_interval: float,
        event_notifier: EventNotifier,
    ):
        super().__init__(refresh_interval, self._refresh)
        event_notifier.register(TuyaResponseReceived, self._update)
        event_notifier.register(TuyaConnectionClosed, lambda _: self.cancel())
        event_notifier.register(TuyaConnectionEstablished, lambda _: self.create())
        self._name = name
        self._notifier = event_notifier
        self._state: Optional[Values] = None

    def __enter__(self) -> "State":
        """Don't start automatically, only when connection is established."""
        return self

    async def _refresh(self) -> None:
        logger.debug("%s: refreshing device state", self._name)
        try:
            await self._notifier.emit(TuyaCommandSent(StateCommand()))
        except CommandTimeoutError:
            logger.warning("%s: timeout waiting for state response", self._name)

    async def _update(self, event: TuyaResponseReceived) -> None:
        if event.response.error:
            pass
        elif isinstance(event.response, StateResponse):
            new_state = event.response.values
            if new_state and self._state != new_state:
                logger.debug("%s: received new device state: %s", self._name, new_state)
                self._state = new_state
                await self._notifier.emit(TuyaStateUpdated(self._state.copy()))
        elif isinstance(event.response, StatusResponse):
            if self._state is None:
                # We have not yet received the initial state.
                # Better discard this as the state might be newer.
                return
            new_state = {**self._state, **event.response.values}
            if self._state != new_state:
                logger.debug(
                    "%s: received device state update: %s",
                    self._name,
                    event.response.values,
                )
                self._state = new_state
                await self._notifier.emit(TuyaStateUpdated(self._state.copy()))
