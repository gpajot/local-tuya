import asyncio
import logging
from typing import Optional, cast

from local_tuya.events import EventNotifier
from local_tuya.protocol import Values
from local_tuya.tuya import TuyaStateUpdated

logger = logging.getLogger(__name__)


class StateHandler:
    def __init__(self, name: str, event_notifier: EventNotifier):
        event_notifier.register(TuyaStateUpdated, self._set)
        self._name = name
        self._state: Optional[Values] = None
        self._updated = asyncio.Event()

    def _set(self, event: TuyaStateUpdated) -> None:
        self._state = event.values
        self._updated.set()

    async def get(self) -> Values:
        if self._state is None:
            await self._updated.wait()
        return cast(Values, self._state).copy()

    async def matches(self, values: Values) -> None:
        """Wait until the device state matches the update values."""

        def _matches() -> bool:
            for k, v in values.items():
                if cast(Values, self._state).get(k) != v:
                    return False
            return True

        if not self._state:
            await self._updated.wait()

        while not _matches():
            self._updated.clear()
            logger.debug("%s: waiting for device state to be updated", self._name)
            await self._updated.wait()
