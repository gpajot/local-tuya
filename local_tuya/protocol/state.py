import logging
from typing import Optional

from concurrent_tasks import PeriodicTask

from local_tuya.errors import CommandTimeoutError
from local_tuya.events import EventNotifier
from local_tuya.protocol.events import (
    CommandSent,
    ConnectionClosed,
    ConnectionEstablished,
    ResponseReceived,
    StateUpdated,
)
from local_tuya.protocol.message import (
    StateCommand,
    StateResponse,
    StatusResponse,
    Values,
)

logger = logging.getLogger(__name__)


class State(PeriodicTask):
    def __init__(
        self,
        refresh_interval: float,
        event_notifier: EventNotifier,
    ):
        super().__init__(refresh_interval, self._refresh)
        event_notifier.register(ResponseReceived, self._update)
        event_notifier.register(ConnectionClosed, lambda _: self.cancel())
        event_notifier.register(ConnectionEstablished, lambda _: self.create())
        self._notifier = event_notifier
        self._state: Optional[Values] = None

    def __enter__(self) -> "State":
        """Don't start automatically, only when connection is established."""
        return self

    async def _refresh(self) -> None:
        logger.debug("refreshing device state")
        try:
            await self._notifier.emit(CommandSent(StateCommand()))
        except CommandTimeoutError:
            logger.warning("timeout waiting for state response")

    async def _update(self, event: ResponseReceived) -> None:
        if event.response.error:
            pass
        elif isinstance(event.response, StateResponse):
            new_state = event.response.values
            if self._state != new_state:
                logger.debug("received new device state: %s", new_state)
                self._state = new_state
                await self._notifier.emit(StateUpdated(new_state.copy()))
        elif isinstance(event.response, StatusResponse):
            if self._state is None:
                # We have not yet received the initial state.
                # Better discard this as the state might be newer.
                return
            new_state = {**self._state, **event.response.values}
            if self._state != new_state:
                logger.debug("received device state update: %s", event.response.values)
                self._state = new_state
                await self._notifier.emit(StateUpdated(new_state.copy()))
