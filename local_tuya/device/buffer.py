import asyncio
import logging
from typing import Optional

from concurrent_tasks import BackgroundTask

from local_tuya.device.constraints import Constraints
from local_tuya.device.state import StateHandler
from local_tuya.protocol import Values
from local_tuya.tuya import TuyaProtocol

logger = logging.getLogger(__name__)


class UpdateBuffer(BackgroundTask):
    """Debounce updates to the device."""

    def __init__(
        self,
        device_name: str,
        delay: float,
        confirm_timeout: float,
        protocol: TuyaProtocol,
        state_handler: StateHandler,
        constraints: Optional[Constraints],
    ):
        super().__init__(self._update)
        self._name = device_name
        self._delay = delay
        self._confirm_timeout = confirm_timeout
        self._protocol = protocol
        self._state_handler = state_handler
        self._constraints = constraints
        self._buffer: Values = {}
        # Used to know we are currently performing an update.
        self._lock = asyncio.Lock()
        self._updated: Optional[asyncio.Future[None]] = None

    async def update(self, values: Values) -> None:
        filtered = await self._filter({**self._buffer, **values})
        if not self._delay:
            if filtered:
                async with self._lock:
                    await self._do_update(filtered)
            return
        self._buffer = filtered
        async with self._lock:
            self.cancel()
            if self._buffer:
                self.create()
                if not self._updated:
                    self._updated = asyncio.Future()
            else:
                logger.debug(
                    "%s: cancelling previous commands as update is no longer required",
                    self._name,
                )
                if self._updated:
                    self._updated.set_result(None)
                    self._updated = None
        if self._updated:
            await self._updated

    async def _update(self) -> None:
        logger.debug(
            "%s: received command waiting %ss before sending to device",
            self._name,
            self._delay,
        )
        await asyncio.sleep(self._delay)
        buffer = self._buffer
        self._buffer = {}
        if buffer:
            async with self._lock:
                try:
                    await self._do_update(buffer)
                    if self._updated:
                        self._updated.set_result(None)
                except Exception as e:
                    if self._updated:
                        self._updated.set_exception(e)
                finally:
                    self._updated = None

    async def _do_update(self, values: Values) -> None:
        logger.debug("%s: updating device with: %s", self._name, values)
        await self._protocol.update(values)
        if not self._confirm_timeout:
            return
        # Wait until we receive real confirmation of update via status.
        await asyncio.wait_for(
            self._state_handler.matches(values),
            self._confirm_timeout,
        )

    async def _filter(self, values: Values) -> Values:
        state = await self._state_handler.get()
        filtered = {k: v for k, v in values.items() if state[k] != v}
        if not self._constraints:
            return filtered
        return self._constraints.filter_values(filtered, state)
