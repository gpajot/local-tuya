from typing import AsyncIterator, Iterator

from imbue import Package, auto_context

from local_tuya.events import EventNotifier
from local_tuya.tuya.config import TuyaConfig
from local_tuya.tuya.heartbeat import Heartbeat
from local_tuya.tuya.message import (
    MessageHandler,
    get_handler,
)
from local_tuya.tuya.protocol import TuyaProtocol
from local_tuya.tuya.receiver import Receiver
from local_tuya.tuya.sender import Sender
from local_tuya.tuya.state import State
from local_tuya.tuya.transport import Transport


class TuyaPackage(Package):
    EXTRA_DEPENDENCIES = (TuyaProtocol,)

    def __init__(self, name: str, config: TuyaConfig):
        self._name = name
        self._cfg = config

    @auto_context
    def event_notifier(self) -> EventNotifier:
        return EventNotifier()

    @auto_context
    def message_handler(self) -> MessageHandler:
        return get_handler(self._cfg)

    @auto_context(eager=True)
    async def transport(
        self, notifier: EventNotifier, message_handler: MessageHandler
    ) -> AsyncIterator[Transport]:
        async with Transport(
            name=self._name,
            address=self._cfg.address,
            port=self._cfg.port,
            separator=message_handler.SUFFIX.to_bytes(length=4, byteorder="big"),
            backoff=self._cfg.connection_backoff,
            timeout=self._cfg.timeout,
            event_notifier=notifier,
        ) as transport:
            yield transport

    @auto_context(eager=True)
    def receiver(
        self,
        message_handler: MessageHandler,
        notifier: EventNotifier,
    ) -> Receiver:
        return Receiver(
            name=self._name,
            message_handler=message_handler,
            event_notifier=notifier,
        )

    @auto_context(eager=True)
    def sender(
        self,
        notifier: EventNotifier,
        msg_handler: MessageHandler,
    ) -> Iterator[Sender]:
        with Sender(
            name=self._name,
            message_handler=msg_handler,
            event_notifier=notifier,
            timeout=self._cfg.timeout,
        ) as sender:
            yield sender

    @auto_context(eager=True)
    async def heartbeat(self, notifier: EventNotifier) -> AsyncIterator[Heartbeat]:
        with Heartbeat(
            name=self._name,
            interval=self._cfg.heartbeat_interval,
            event_notifier=notifier,
        ) as heartbeat:
            yield heartbeat

    @auto_context(eager=True)
    async def state_keeper(self, notifier: EventNotifier) -> AsyncIterator[State]:
        with State(
            name=self._name,
            refresh_interval=self._cfg.state_refresh_interval,
            event_notifier=notifier,
        ) as state_keeper:
            yield state_keeper
