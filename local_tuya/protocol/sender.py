import asyncio
import logging
from contextlib import AbstractAsyncContextManager
from functools import partial
from typing import Dict, Optional, Tuple, Type

from concurrent_tasks import RestartableTask

from local_tuya.errors import CommandTimeoutError
from local_tuya.events import EventNotifier
from local_tuya.protocol.events import (
    CommandSent,
    ConnectionEstablished,
    ConnectionLost,
    DataSent,
    ResponseReceived,
)
from local_tuya.protocol.message import Command, HeartbeatCommand, MessageHandler

logger = logging.getLogger(__name__)


class Sender(AbstractAsyncContextManager):
    def __init__(
        self,
        message_handler: MessageHandler,
        event_notifier: EventNotifier,
        timeout: float,
    ):
        event_notifier.register(ConnectionEstablished, self._connection_established)
        event_notifier.register(ConnectionLost, self._connection_lost)
        event_notifier.register(ResponseReceived, self._receive_response)
        event_notifier.register(CommandSent, self._send)
        self._notifier = event_notifier
        self._handler = message_handler
        self._timeout = timeout
        self._pending_tasks: Dict[
            Tuple[int, Optional[Type[Command]]], RestartableTask[None]
        ] = {}
        self._can_send = False
        self._sequence_number = 0

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        # This has to be async to let task cancellation be effective.
        for task in self._pending_tasks.values():
            task.cancel()

    def _connection_established(self, _: ConnectionEstablished) -> None:
        self._can_send = True
        for task in self._pending_tasks.values():
            task.start()

    def _connection_lost(self, _: ConnectionLost) -> None:
        self._can_send = False
        for task in self._pending_tasks.values():
            task.cancel()

    def _receive_response(self, event: ResponseReceived) -> None:
        task = self._pending_tasks.pop(
            (event.sequence_number, event.command_class), None
        )
        if task:
            if event.response.error:
                task.set_exception(event.response.error)
            else:
                task.set_result(None)

    async def _send(self, event: CommandSent) -> None:
        """Send a message, waiting for the response.
        Timeout is for waiting the response, it will wait until a connection can be acquired.
        """
        sequence_number = self._get_sequence_number(event.command)
        logger.debug(
            "sending message %i %s", sequence_number, event.command.__class__.__name__
        )
        data = self._handler.pack(sequence_number, event.command)
        task = RestartableTask[None](
            partial(self._notifier.emit, DataSent(data)),
            timeout=self._timeout,
        )
        if self._can_send:
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
