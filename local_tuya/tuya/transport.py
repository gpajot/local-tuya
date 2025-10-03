import asyncio
import logging
from contextlib import AbstractContextManager, AsyncExitStack
from functools import partial
from typing import Self

from concurrent_tasks import BackgroundTask, RobustStream

from local_tuya.backoff import SequenceBackoff
from local_tuya.events import EventNotifier
from local_tuya.tuya.events import (
    TuyaCommandSent,
    TuyaConnectionClosed,
    TuyaConnectionEstablished,
    TuyaResponseReceived,
)
from local_tuya.tuya.message import Command, HeartbeatCommand, MessageHandler

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


class SequenceNumberGetter(AbstractContextManager):
    def __init__(self):
        self._num = 0

    def __call__(self, command: Command) -> int:
        if isinstance(command, HeartbeatCommand):
            # Devices return 0 whatever is sent.
            return 0
        if self._num == 1000:
            self._num = 1
        else:
            self._num += 1
        return self._num

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._num = 0


class Transport(AsyncExitStack):
    def __init__(
        self,
        name: str,
        address: str,
        port: int,
        backoff: SequenceBackoff,
        timeout: float,
        keepalive: float,
        message_handler: MessageHandler,
        event_notifier: EventNotifier,
    ):
        super().__init__()
        self._stream = TuyaStream(name, address, port, backoff, timeout, event_notifier)
        event_notifier.register(TuyaCommandSent, self._write)
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
        self._keepalive = keepalive
        self._msg_handler = message_handler
        self._msg_errors = 0
        self._get_seq_number = SequenceNumberGetter()
        self._notifier = event_notifier
        self._reader: asyncio.StreamReader | None = None

        self._receive_task = BackgroundTask(self._receive)
        self._reconnect_task = BackgroundTask(self._reconnect)

    async def __aenter__(self) -> Self:
        self.enter_context(self._get_seq_number)
        await self.enter_async_context(self._stream)
        self.enter_context(self._receive_task)
        return self

    async def _receive(self) -> None:
        self._reader = self._stream.reader
        try:
            while True:
                data = await self._reader.readuntil(self._msg_handler.separator)
                # While no data has been received, we assume the connection is not necessarily healthy.
                # It is possible to be connected and not be able to communicated with the device.
                # We assume the connection to be healthy when we receive responses.
                # As long as it is unhealthy, connection attempts will increase the backoff.
                self._backoff.reset()
                self._reconnect_task.create()
                try:
                    (
                        sequence_number,
                        response,
                        command_class,
                    ) = self._msg_handler.unpack(data)
                except Exception:
                    logger.warning("error processing message", exc_info=True)
                    # Allow 2 errors then reconnect on the 3rd.
                    if self._msg_errors > 2:
                        self._stream.reconnect()
                        self._msg_errors = 0
                    else:
                        self._msg_errors += 1
                    continue
                self._msg_errors = 0
                logger.debug(
                    "%s: received message %i %s",
                    self._name,
                    sequence_number,
                    response.__class__.__name__,
                )
                await self._notifier.emit(
                    TuyaResponseReceived(
                        sequence_number,
                        response,
                        command_class,
                    )
                )
        finally:
            self._reader = None

    async def _write(self, event: TuyaCommandSent) -> None:
        sequence_number = self._get_seq_number(event.command)
        logger.debug(
            "%s: sending message %i %s",
            self._name,
            sequence_number,
            event.command.__class__.__name__,
        )
        data = self._msg_handler.pack(sequence_number, event.command)
        await self._stream.write(data)

    async def _reconnect(self) -> None:
        await asyncio.sleep(self._keepalive)
        self._stream.reconnect()
