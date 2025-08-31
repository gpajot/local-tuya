import asyncio
import logging
from contextlib import AsyncExitStack
from functools import partial

from concurrent_tasks import BackgroundTask, RobustStream
from typing_extensions import Self  # 3.11

from local_tuya.backoff import Backoff
from local_tuya.events import EventNotifier
from local_tuya.tuya.events import (
    TuyaConnectionClosed,
    TuyaConnectionEstablished,
    TuyaDataReceived,
    TuyaDataSent,
    TuyaResponseReceived,
)

logger = logging.getLogger(__name__)


class TuyaStream(RobustStream):
    def __init__(
        self,
        name: str,
        address: str,
        port: int,
        backoff: Backoff,
        timeout: float,
        event_notifier: EventNotifier,
    ):
        super().__init__(
            connector=partial(
                asyncio.get_running_loop().create_connection,
                host=address,
                port=port,
            ),
            name=name,
            backoff=backoff.wait,
            timeout=timeout,
        )
        self._notifier = event_notifier

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._notifier.emit(TuyaConnectionClosed(None))
        await super().__aexit__(exc_type, exc_val, exc_tb)

    async def _connect(self) -> None:
        if self._last_exc:
            await self._notifier.emit(TuyaConnectionClosed(self._last_exc))
        await super()._connect()
        await self._notifier.emit(TuyaConnectionEstablished())


class Transport(AsyncExitStack):
    def __init__(
        self,
        name: str,
        address: str,
        port: int,
        separator: bytes,
        backoff: Backoff,
        timeout: float,
        event_notifier: EventNotifier,
    ):
        super().__init__()
        self._stream = TuyaStream(name, address, port, backoff, timeout, event_notifier)
        event_notifier.register(TuyaDataSent, self._write)
        event_notifier.register(TuyaResponseReceived, self._connection_live)
        self._name = name
        self._backoff = backoff
        self._separator = separator
        self._notifier = event_notifier

        self._receive_task = BackgroundTask(self._receive)

    async def __aenter__(self) -> Self:
        await self.enter_async_context(self._stream)
        self.enter_context(self._receive_task)
        return self

    def _connection_live(self, _: TuyaResponseReceived) -> None:
        # While this event has not been received, we assume the connection is not necessarily healthy.
        # It is possible to be connected and not be able to communicated with the device.
        # We assume the connection to be healthy when we receive responses.
        # As long as it is unhealthy, connection attempts will increase the backoff.
        self._backoff.reset()

    async def _receive(self) -> None:
        reader = self._stream.reader
        while True:
            data = await reader.readuntil(self._separator)
            await self._notifier.emit(TuyaDataReceived(data))

    async def _write(self, data: TuyaDataSent) -> None:
        await self._stream.write(data)
