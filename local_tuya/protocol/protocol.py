import asyncio
from contextlib import AsyncExitStack
from typing import Awaitable, Callable, Optional

from local_tuya.events import EventNotifier
from local_tuya.protocol.config import ProtocolConfig
from local_tuya.protocol.events import CommandSent, StateUpdated
from local_tuya.protocol.heartbeat import Heartbeat
from local_tuya.protocol.message import (
    MessageHandler,
    UpdateCommand,
    Values,
    get_handler,
)
from local_tuya.protocol.receiver import Receiver
from local_tuya.protocol.sender import Sender
from local_tuya.protocol.state import State
from local_tuya.protocol.transport import Transport


def _state_updated_callback(
    func: Callable[[Values], Awaitable]
) -> Callable[[StateUpdated], Awaitable]:
    async def _wrapper(event: StateUpdated) -> None:
        await func(event.values)

    return _wrapper


class Protocol(asyncio.Protocol, AsyncExitStack):
    def __init__(
        self,
        config: ProtocolConfig,
        state_updated_callback: Optional[Callable[[Values], Awaitable]] = None,
    ):
        super().__init__()
        self._config = config
        self._event_notifier = EventNotifier()
        if state_updated_callback:
            self._event_notifier.register(
                StateUpdated,
                _state_updated_callback(state_updated_callback),
            )
        message_handler: MessageHandler = get_handler(config)
        self._transport = Transport(
            address=config.address,
            port=config.port,
            backoff=config.connection_backoff,
            event_notifier=self._event_notifier,
        )
        self._sender = Sender(
            message_handler=message_handler,
            event_notifier=self._event_notifier,
            timeout=config.timeout,
        )
        self._receiver = Receiver(
            message_handler=message_handler,
            event_notifier=self._event_notifier,
        )
        self._heartbeat = Heartbeat(
            interval=config.heartbeat_interval,
            event_notifier=self._event_notifier,
        )
        self._state_keeper = State(
            refresh_interval=config.state_refresh_interval,
            event_notifier=self._event_notifier,
        )

    async def __aenter__(self):
        await self.enter_async_context(self._transport)
        await self.enter_async_context(self._sender)
        self.enter_context(self._heartbeat)
        self.enter_context(self._state_keeper)
        return self

    async def update(self, values: Values) -> None:
        """Update the device."""
        await self._event_notifier.emit(CommandSent(UpdateCommand(values)))
