import asyncio
import logging
from contextlib import AsyncExitStack
from functools import partial
from typing import Self

from concurrent_tasks import BackgroundTask, RobustStream

from local_tuya.backoff import SequenceBackoff
from local_tuya.events import EventNotifier
from local_tuya.tuya.events import (
    TuyaConnectionClosed,
    TuyaConnectionEstablished,
    TuyaDataReceived,
    TuyaDataSent,
)

logger = logging.getLogger(__name__)


class TuyaStream(RobustStream):
    def __init__(
        self,
        name: str,
        address: str,
        port: int,
        backoff: SequenceBackoff,
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
        self._first_connect = True

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._notifier.emit(TuyaConnectionClosed(None))
        await super().__aexit__(exc_type, exc_val, exc_tb)

    async def _connect(self) -> None:
        if self._first_connect:
            self._first_connect = False
        else:
            await self._notifier.emit(TuyaConnectionClosed(self._last_exc))
        await super()._connect()
        await self._notifier.emit(TuyaConnectionEstablished())

    def reconnect(self) -> None:
        if self._transport:
            self._transport.close()


class Transport(AsyncExitStack):
    def __init__(
        self,
        name: str,
        address: str,
        port: int,
        separator: bytes,
        backoff: SequenceBackoff,
        timeout: float,
        keepalive: float,
        event_notifier: EventNotifier,
    ):
        super().__init__()
        self._stream = TuyaStream(name, address, port, backoff, timeout, event_notifier)
        event_notifier.register(TuyaDataSent, self._write)
        event_notifier.register(
            TuyaConnectionEstablished,
            lambda _: self._reconnect_task.create(),
        )
        event_notifier.register(
            TuyaConnectionClosed,
            lambda _: self._reconnect_task.cancel(),
        )
        self._name = name
        self._backoff = backoff
        self._separator = separator
        self._keepalive = keepalive
        self._notifier = event_notifier
        self._reader: asyncio.StreamReader | None = None

        self._receive_task = BackgroundTask(self._receive)
        self._reconnect_task = BackgroundTask(self._reconnect)

    async def __aenter__(self) -> Self:
        await self.enter_async_context(self._stream)
        self.enter_context(self._receive_task)
        return self

    async def _receive(self) -> None:
        self._reader = self._stream.reader
        try:
            while True:
                data = await self._reader.readuntil(self._separator)
                # While no data has been received, we assume the connection is not necessarily healthy.
                # It is possible to be connected and not be able to communicated with the device.
                # We assume the connection to be healthy when we receive responses.
                # As long as it is unhealthy, connection attempts will increase the backoff.
                self._backoff.reset()
                self._reconnect_task.create()
                await self._notifier.emit(TuyaDataReceived(data))
        finally:
            self._reader = None

    async def _write(self, data: TuyaDataSent) -> None:
        await self._stream.write(data)

    async def _reconnect(self) -> None:
        await asyncio.sleep(self._keepalive)
        self._stream.reconnect()
