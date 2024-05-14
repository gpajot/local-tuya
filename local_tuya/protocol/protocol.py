from dataclasses import dataclass

from local_tuya.events import EventNotifier
from local_tuya.protocol.events import CommandSent
from local_tuya.protocol.message import (
    UpdateCommand,
    Values,
)
from local_tuya.protocol.transport import Transport


@dataclass
class Protocol:
    event_notifier: EventNotifier
    transport: Transport

    async def update(self, values: Values) -> None:
        """Update the device."""
        await self.event_notifier.emit(CommandSent(UpdateCommand(values)))

    def connect(self) -> None:
        self.transport.connect()
