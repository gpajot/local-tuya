import asyncio
import logging
from typing import Awaitable, Callable, Optional, cast

from local_tuya.protocol import Values

logger = logging.getLogger(__name__)


class StateHandler:
    def __init__(self, updated_callback: Callable[[Values], Awaitable]):
        self._state: Optional[Values] = None
        self._updated_event = asyncio.Event()
        self._updated_callback = updated_callback

    async def updated(self, state: Values) -> None:
        self._state = state
        self._updated_event.set()
        await self._updated_callback(state)

    async def state(self) -> Values:
        if self._state is None:
            await self._updated_event.wait()
        return cast(Values, self._state).copy()

    async def matches(self, values: Values) -> None:
        """Wait until the device state matches the update values."""
        if not self._state:
            await self._updated_event.wait()

        def _matches() -> bool:
            for k, v in values.items():
                if cast(Values, self._state).get(k) != v:
                    return False
            return True

        while not _matches():
            self._updated_event.clear()
            logger.debug("waiting for device state to be updated")
            await self._updated_event.wait()
