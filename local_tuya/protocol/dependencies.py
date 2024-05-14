from typing import AsyncIterator

from imbue import ContextualizedDependency, Package, auto_context

from local_tuya.events import EventNotifier
from local_tuya.protocol.config import ProtocolConfig
from local_tuya.protocol.heartbeat import Heartbeat
from local_tuya.protocol.message import (
    MessageHandler,
    get_handler,
)
from local_tuya.protocol.protocol import Protocol
from local_tuya.protocol.receiver import Receiver
from local_tuya.protocol.sender import Sender
from local_tuya.protocol.state import State
from local_tuya.protocol.transport import Transport


class ProtocolPackage(Package):
    EXTRA_DEPENDENCIES = (
        ContextualizedDependency(Receiver, eager=True),
        Protocol,
    )

    def __init__(self, config: ProtocolConfig):
        self._cfg = config

    @auto_context
    def event_notifier(self) -> EventNotifier:
        return EventNotifier()

    @auto_context
    def message_handler(self) -> MessageHandler:
        return get_handler(self._cfg)

    @auto_context(eager=True)
    async def transport(self, notifier: EventNotifier) -> AsyncIterator[Transport]:
        async with Transport(
            address=self._cfg.address,
            port=self._cfg.port,
            backoff=self._cfg.connection_backoff,
            timeout=self._cfg.timeout,
            event_notifier=notifier,
        ) as transport:
            yield transport

    @auto_context(eager=True)
    async def sender(
        self,
        notifier: EventNotifier,
        msg_handler: MessageHandler,
    ) -> AsyncIterator[Sender]:
        async with Sender(
            message_handler=msg_handler,
            event_notifier=notifier,
            timeout=self._cfg.timeout,
        ) as sender:
            yield sender

    @auto_context(eager=True)
    async def heartbeat(self, notifier: EventNotifier) -> AsyncIterator[Heartbeat]:
        with Heartbeat(
            interval=self._cfg.heartbeat_interval,
            event_notifier=notifier,
        ) as heartbeat:
            yield heartbeat

    @auto_context(eager=True)
    async def state_keeper(self, notifier: EventNotifier) -> AsyncIterator[State]:
        with State(
            refresh_interval=self._cfg.state_refresh_interval,
            event_notifier=notifier,
        ) as state_keeper:
            yield state_keeper
