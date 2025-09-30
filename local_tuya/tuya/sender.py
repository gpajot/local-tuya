import asyncio
import logging
from contextlib import AbstractContextManager
from functools import partial

from local_tuya.errors import CommandTimeoutError
from local_tuya.events import EventNotifier
from local_tuya.tuya.events import (
    TuyaCommandSent,
    TuyaConnectionClosed,
    TuyaDataSent,
    TuyaResponseReceived,
)
from local_tuya.tuya.message import Command, HeartbeatCommand, MessageHandler

logger = logging.getLogger(__name__)


class Sender(AbstractContextManager):
    def __init__(
        self,
        name: str,
        message_handler: MessageHandler,
        event_notifier: EventNotifier,
        timeout: float,
    ):
        event_notifier.register(TuyaConnectionClosed, self._connection_lost)
        event_notifier.register(TuyaResponseReceived, self._receive_response)
        event_notifier.register(TuyaCommandSent, self._send)
        self._name = name
        self._notifier = event_notifier
        self._handler = message_handler
        self._timeout = timeout
        self._pending: dict[tuple[int, type[Command]], asyncio.Future[None]] = {}
        self._sequence_number = 0

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        for future in self._pending.values():
            future.cancel()
        self._pending = {}
        self._sequence_number = 0

    def _connection_lost(self, event: TuyaConnectionClosed) -> None:
        for future in self._pending.values():
            future.set_exception(event.error or ConnectionError("disconnected"))

    def _receive_response(self, event: TuyaResponseReceived) -> None:
        if event.command_class is None:
            return
        if future := self._pending.pop(
            (event.sequence_number, event.command_class), None
        ):
            if event.response.error:
                future.set_exception(event.response.error)
            else:
                future.set_result(None)

    async def _send(self, event: TuyaCommandSent) -> None:
        """Send a message, waiting for the response.
        Timeout is for waiting for the response, only.
        Waiting for the connection to be available is excluded.
        """
        sequence_number = self._get_sequence_number(event.command)
        logger.debug(
            "%s: sending message %i %s",
            self._name,
            sequence_number,
            event.command.__class__.__name__,
        )
        data = self._handler.pack(sequence_number, event.command)
        future = asyncio.Future[None]()
        key = (sequence_number, type(event.command))
        future.add_done_callback(partial(self._done_callback, key))
        self._pending[key] = future
        try:
            async with asyncio.timeout(self._timeout):
                await self._notifier.emit(TuyaDataSent(data))
                await future
        except asyncio.TimeoutError as e:
            raise CommandTimeoutError() from e

    def _get_sequence_number(self, command: Command) -> int:
        if isinstance(command, HeartbeatCommand):
            # Devices return 0 whatever is sent.
            return 0
        if self._sequence_number == 1000:
            self._sequence_number = 1
        else:
            self._sequence_number += 1
        return self._sequence_number

    def _done_callback(
        self,
        key: tuple[int, type[Command]],
        future: asyncio.Future[None],
    ) -> None:
        if self._pending.get(key) is future:
            del self._pending[key]
