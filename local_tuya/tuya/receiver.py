import logging

from local_tuya.events import EventNotifier
from local_tuya.tuya.events import (
    TuyaDataReceived,
    TuyaResponseReceived,
)
from local_tuya.tuya.message import MessageHandler

logger = logging.getLogger(__name__)


class Receiver:
    def __init__(
        self,
        name: str,
        message_handler: MessageHandler,
        event_notifier: EventNotifier,
    ):
        event_notifier.register(TuyaDataReceived, self._receive_messages)
        self._name = name
        self._handler = message_handler
        self._notifier = event_notifier

    async def _receive_messages(self, data: TuyaDataReceived) -> None:
        (
            sequence_number,
            response,
            command_class,
            remaining,
        ) = self._handler.unpack(data)
        if not response:
            logger.warning("%s: received incomplete message", self._name)
            return
        if remaining:
            logger.warning("%s: received a message larger than expected")
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
