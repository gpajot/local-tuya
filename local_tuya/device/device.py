import asyncio
import logging
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
from functools import partial
from typing import ClassVar, Collection, Optional, Union

from concurrent_tasks import TaskPool

from local_tuya.device.buffer import UpdateBuffer
from local_tuya.device.config import DeviceConfig
from local_tuya.device.constraints import Constraints
from local_tuya.device.state import StateHandler
from local_tuya.events import EventNotifier
from local_tuya.protocol import DeviceDiscovery, Protocol, Values
from local_tuya.tuya import (
    TuyaConnectionClosed,
    TuyaConnectionEstablished,
    TuyaProtocol,
    TuyaStateUpdated,
)

logger = logging.getLogger(__name__)


class Device(AsyncExitStack, ABC):
    DISCOVERY: ClassVar[DeviceDiscovery]
    CONSTRAINTS: ClassVar[Optional[Constraints]] = None

    def __init__(
        self,
        name: str,
        config: DeviceConfig,
        protocol: Protocol,
        event_notifier: EventNotifier,
        tuya_protocol: TuyaProtocol,
    ):
        super().__init__()
        self._name = name
        self._cfg = config

        self._protocol = protocol
        self._tuya_protocol = tuya_protocol
        self._buffer = UpdateBuffer(
            device_name=self._name,
            delay=config.debounce_updates,
            confirm_timeout=config.confirm_timeout,
            protocol=tuya_protocol,
            state_handler=StateHandler(self._name, event_notifier),
            constraints=self.CONSTRAINTS,
        )
        event_notifier.register(TuyaStateUpdated, self._update_state)
        event_notifier.register(TuyaConnectionEstablished, self._set_availability)
        event_notifier.register(TuyaConnectionClosed, self._set_availability)

        # Run in task pools to buffer traffic and avoid blocking the device.
        self._send_task_pool = TaskPool(
            size=1,
            timeout=self._protocol.timeout,
        )
        self._receive_task_pool = TaskPool(
            size=1,
            timeout=config.tuya.timeout + config.confirm_timeout,
        )

    @classmethod
    @abstractmethod
    def filter_data_points(
        cls, included_components: Optional[Collection[str]]
    ) -> set[str]: ...

    @abstractmethod
    def _from_tuya_payload(self, tuya_payload: Values) -> Values: ...

    @abstractmethod
    def _to_tuya_payload(self, payload: Values) -> Values: ...

    async def __aenter__(self):
        logger.debug("%s: initializing...", self._name)
        await self.enter_async_context(self._send_task_pool)
        await self.enter_async_context(self._receive_task_pool)
        if self._cfg.enable_discovery:
            self._check_future(
                self._send_task_pool.create_task(
                    self._protocol.send_discovery(
                        self.DISCOVERY.filter_components(self._cfg.included_components),
                        self._cfg.tuya.id_,
                        self._name,
                    ),
                ),
                task="sending discovery",
            )
        self.callback(self._buffer.cancel)
        await self.enter_async_context(self._tuya_protocol.initialize())
        return self

    def _update_state(self, event: TuyaStateUpdated) -> None:
        state = self._from_tuya_payload(event.values)
        logger.debug("%s: received new device state: %s", self._name, state)
        self._check_future(
            self._send_task_pool.create_task(
                self._protocol.send_state(self._cfg.tuya.id_, state),
            ),
            task="sending state update",
        )

    def _set_availability(
        self, event: Union[TuyaConnectionEstablished, TuyaConnectionClosed]
    ) -> None:
        self._check_future(
            self._send_task_pool.create_task(
                self._protocol.set_availability(
                    self._cfg.tuya.id_,
                    isinstance(event, TuyaConnectionEstablished),
                )
            ),
            task="setting availability",
        )

    def update(self, payload: Values) -> None:
        try:
            tuya_payload = self._to_tuya_payload(payload)
        except Exception:
            logger.warning(
                "%s: could no load tuya payload from %s",
                self._name,
                payload,
                exc_info=True,
            )
            return
        logger.debug("%s: received command: %s", self._name, tuya_payload)
        self._check_future(
            self._receive_task_pool.create_task(self._buffer.update(tuya_payload)),
            task="sending command to device",
        )

    def _check_future(self, future: asyncio.Future, *, task: str) -> None:
        """Add a callback to warn if errors are raised in background tasks
        otherwise they would be silenced."""
        future.add_done_callback(partial(self._log_task_exceptions, task))

    def _log_task_exceptions(self, task: str, future: asyncio.Future) -> None:
        if future.cancelled():
            return
        try:
            future.result()
        except TimeoutError:
            logger.error("%s: timeout %s", self._name, task)
        except Exception:
            logger.error("%s: exception caught", self._name, exc_info=True)
