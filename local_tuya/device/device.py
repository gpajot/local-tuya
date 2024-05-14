import asyncio
import logging
from contextlib import AsyncExitStack
from typing import AsyncIterator, Callable, Generic, Optional, TypeVar, cast

from imbue import Container

from local_tuya.device.buffer import UpdateBuffer
from local_tuya.device.config import DeviceConfig
from local_tuya.device.constraints import Constraints
from local_tuya.device.dependencies import DevicePackage
from local_tuya.device.enums import State
from local_tuya.device.state import StateHandler
from local_tuya.events import EventNotifier
from local_tuya.protocol import Protocol, ProtocolPackage, StateUpdated, Values

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=State)


class Device(AsyncExitStack, Generic[T]):
    def __init__(
        self,
        config: DeviceConfig,
        load_state: Callable[[Values], T],
        constraints: Optional[Constraints] = None,
    ):
        super().__init__()
        self._load_state = load_state
        self._container = Container(
            DevicePackage(config, constraints),
            ProtocolPackage(config.protocol),
        ).application_context()
        self._state_handler: Optional[StateHandler] = None
        self._buffer: Optional[UpdateBuffer] = None
        self._last_state: Optional[T] = None
        self._state_updated = asyncio.Event()

    async def __aenter__(self):
        await self.enter_async_context(self._container)
        self._state_handler = await self._container.get(StateHandler)
        self._buffer = await self._container.get(UpdateBuffer)
        event_notifier = await self._container.get(EventNotifier)
        event_notifier.register(StateUpdated, self._update_last_state)
        (await self._container.get(Protocol)).connect()
        return self

    async def state(self) -> AsyncIterator[T]:
        if self._last_state:
            yield self._last_state
        while True:
            await self._state_updated.wait()
            self._state_updated.clear()
            yield cast(T, self._last_state)

    def _update_last_state(self, event: StateUpdated) -> None:
        self._last_state = self._load_state(event.values)
        logger.debug("received new device state: %s", self._last_state)
        self._state_updated.set()

    async def _state(self) -> T:
        if not self._state_handler:
            raise RuntimeError(f"{self:r} context has not been entered")
        return self._load_state(await self._state_handler.get())

    async def _update(self, values: Values) -> None:
        if not self._buffer:
            raise RuntimeError(f"{self:r} context has not been entered")
        await self._buffer.update(values)
