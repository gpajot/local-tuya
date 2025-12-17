import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Collection
from contextlib import AsyncExitStack
from functools import partial
from typing import ClassVar

from concurrent_tasks import TaskPool

from local_tuya.device.buffer import UpdateBuffer
from local_tuya.device.config import DeviceConfig
from local_tuya.device.constraints import Constraints
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
    CONSTRAINTS: ClassVar[Constraints | None] = None

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
            protocol=tuya_protocol,
            event_notifier=event_notifier,
            constraints=self.CONSTRAINTS,
            retries=config.retries,
            retry_backoff=config.retry_backoff,
        )
        event_notifier.register(TuyaStateUpdated, self._update_state)
        event_notifier.register(TuyaConnectionEstablished, self._set_availability)
        event_notifier.register(TuyaConnectionClosed, self._set_availability)

        # Run in task pools to buffer traffic and avoid blocking the device.
        self._protocol_pool = TaskPool(size=2, timeout=self._protocol.timeout)
        self._tuya_pool = TaskPool(size=2, timeout=config.tuya.timeout)

    @classmethod
    @abstractmethod
    def filter_data_points(
        cls, included_components: Collection[str] | None
    ) -> set[str]: ...

    @abstractmethod
    def _from_tuya_payload(self, tuya_payload: Values) -> Values: ...

    @abstractmethod
    def _to_tuya_payload(self, payload: Values) -> Values: ...

    async def __aenter__(self):
        logger.debug("%s: initializing...", self._name)
        await self.enter_async_context(self._protocol_pool)
        await self.enter_async_context(self._tuya_pool)
        if self._cfg.enable_discovery:
            self._check_future(
                self._protocol_pool.create_task(
                    self._protocol.send_discovery(
                        self.DISCOVERY.filter_components(self._cfg.included_components),
                        self._cfg.tuya.id_,
                        self._name,
                    ),
                ),
                task="sending discovery",
            )
        self.callback(self._buffer.close)
        await self.enter_async_context(self._tuya_protocol.initialize())
        return self

    def _update_state(self, event: TuyaStateUpdated) -> None:
        state = self._from_tuya_payload(event.values)
        logger.debug("%s: received new device state: %s", self._name, state)
        self._check_future(
            self._protocol_pool.create_task(
                self._protocol.send_state(self._cfg.tuya.id_, state),
            ),
            task="sending state update",
        )

    def _set_availability(
        self, event: TuyaConnectionEstablished | TuyaConnectionClosed
    ) -> None:
        self._check_future(
            self._protocol_pool.create_task(
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
            logger.error(
                "%s: could no load tuya payload from %s",
                self._name,
                payload,
                exc_info=True,
            )
            return
        logger.debug("%s: received command: %s", self._name, tuya_payload)
        self._check_future(
            self._tuya_pool.create_task(self._buffer.update(tuya_payload)),
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
