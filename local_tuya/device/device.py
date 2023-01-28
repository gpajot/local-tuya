import logging
from contextlib import AsyncExitStack
from typing import Any, Awaitable, Callable, Generic, Optional, TypeVar

from local_tuya.device.buffer import UpdateBuffer
from local_tuya.device.config import DeviceConfig
from local_tuya.device.constraints import Constraints
from local_tuya.device.enums import State
from local_tuya.device.state import StateHandler
from local_tuya.events import maybe_async
from local_tuya.protocol import Protocol, Values

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=State)


class Device(AsyncExitStack, Generic[T]):
    def __init__(
        self,
        config: DeviceConfig,
        load_state: Callable[[Values], T],
        state_updated_callback: Optional[Callable[[T], Any]] = None,
        constraints: Optional[Constraints] = None,
    ):
        super().__init__()
        self._load_state = load_state
        self._state_updated_callback_func: Optional[Callable[[T], Awaitable]] = (
            maybe_async(state_updated_callback) if state_updated_callback else None
        )
        self._state_handler = StateHandler(self._state_updated_callback)
        self._protocol = Protocol(
            config.protocol,
            self._state_handler.updated,
        )
        self._buffer = UpdateBuffer(
            delay=config.debounce_updates,
            confirm_timeout=config.confirm_timeout,
            protocol=self._protocol,
            state_handler=self._state_handler,
            constraints=constraints,
        )

    async def __aenter__(self):
        await self.enter_async_context(self._protocol)
        self.enter_context(self._buffer)
        return self

    def set_state_updated_callback(self, callback: Callable[[T], Any]) -> None:
        self._state_updated_callback_func = maybe_async(callback)

    async def _state(self) -> T:
        return self._load_state(await self._state_handler.state())

    async def _update(self, values: Values) -> None:
        await self._buffer.update(values)

    async def _state_updated_callback(self, values: Values) -> None:
        state = self._load_state(values)
        logger.info("received new device state: %s", state)
        if self._state_updated_callback_func:
            await self._state_updated_callback_func(state)
