import logging

from local_tuya.events import EventNotifier
from local_tuya.protocol.events import ConnectionLost, DataReceived, ResponseReceived
from local_tuya.protocol.message import MessageHandler

logger = logging.getLogger(__name__)


class Receiver:
    def __init__(
        self,
        message_handler: MessageHandler,
        event_notifier: EventNotifier,
    ):
        event_notifier.register(DataReceived, self._receive_messages)
        event_notifier.register(ConnectionLost, self._reset)
        self._handler = message_handler
        self._notifier = event_notifier
        self._buffer = b""

    def _reset(self, _: ConnectionLost) -> None:
        self._buffer = b""

    async def _receive_messages(self, data: DataReceived) -> None:
        self._buffer += data
        try:
            # Get all message from the data.
            while self._buffer:
                (
                    sequence_number,
                    response,
                    command_class,
                    self._buffer,
                ) = self._handler.unpack(self._buffer)
                if not response:
                    # We need more data to build a response.
                    break
                logger.debug(
                    "received message %i %s",
                    sequence_number,
                    response.__class__.__name__,
                )
                await self._notifier.emit(
                    ResponseReceived(
                        sequence_number,
                        response,
                        command_class,
                    )
                )
        except Exception:
            # Reset the buffer.
            self._buffer = b""
