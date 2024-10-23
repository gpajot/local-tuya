from dataclasses import dataclass
from typing import AsyncContextManager

from local_tuya.events import EventNotifier
from local_tuya.protocol import Values
from local_tuya.tuya.events import TuyaCommandSent
from local_tuya.tuya.message import (
    UpdateCommand,
)
from local_tuya.tuya.transport import Transport


@dataclass
class TuyaProtocol:
    event_notifier: EventNotifier
    transport: Transport

    async def update(self, values: Values) -> None:
        """Update the device."""
        await self.event_notifier.emit(TuyaCommandSent(UpdateCommand(values)))

    def initialize(self) -> AsyncContextManager:
        return self.transport
