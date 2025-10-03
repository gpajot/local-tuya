from dataclasses import dataclass

from local_tuya.events import Event
from local_tuya.protocol import Values
from local_tuya.tuya.message import Command, Response


class TuyaConnectionEstablished(Event): ...


@dataclass
class TuyaConnectionClosed(Event):
    error: Exception | None


@dataclass
class TuyaCommandSent(Event):
    command: Command


@dataclass
class TuyaResponseReceived(Event):
    sequence_number: int
    response: Response
    command_class: type[Command] | None


@dataclass
class TuyaStateUpdated(Event):
    values: Values
