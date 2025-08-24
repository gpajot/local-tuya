import asyncio
import logging
from contextlib import AbstractContextManager
from functools import partial
from typing import Optional

from concurrent_tasks import RestartableTask

from local_tuya.errors import CommandTimeoutError
from local_tuya.events import EventNotifier
from local_tuya.tuya.events import (
    TuyaCommandSent,
    TuyaConnectionClosed,
    TuyaConnectionEstablished,
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
        event_notifier.register(TuyaConnectionEstablished, self._connection_established)
        event_notifier.register(TuyaConnectionClosed, self._connection_lost)
        event_notifier.register(TuyaResponseReceived, self._receive_response)
        event_notifier.register(TuyaCommandSent, self._send)
        self._name = name
        self._notifier = event_notifier
        self._handler = message_handler
        self._timeout = timeout
        self._pending_tasks: dict[
            tuple[int, Optional[type[Command]]], RestartableTask[None]
        ] = {}
        self._can_send = asyncio.Event()
        self._sequence_number = 0

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        for task in self._pending_tasks.values():
            task.cancel()
        self._pending_tasks = {}
        self._can_send.clear()
        self._sequence_number = 0

    def _connection_established(self, _: TuyaConnectionEstablished) -> None:
        for task in self._pending_tasks.values():
            task.start()
        self._can_send.set()

    def _connection_lost(self, _: TuyaConnectionClosed) -> None:
        self._can_send.clear()
        for task in self._pending_tasks.values():
            task.cancel()

    def _receive_response(self, event: TuyaResponseReceived) -> None:
        task = self._pending_tasks.pop(
            (event.sequence_number, event.command_class), None
        )
        if task:
            if event.response.error:
                task.set_exception(event.response.error)
            else:
                task.set_result(None)

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
        await self._can_send.wait()
        task = RestartableTask[None](
            partial(self._notifier.emit, TuyaDataSent(data)),
            timeout=self._timeout,
        )
        task.start()
        self._pending_tasks[(sequence_number, type(event.command))] = task
        try:
            await task
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
