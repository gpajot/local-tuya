from dataclasses import dataclass
from typing import Optional, Type

from local_tuya.events import Event
from local_tuya.protocol.message import Command, Response, Values


class ConnectionEstablished(Event):
    ...


@dataclass
class ConnectionLost(Event):
    error: Optional[Exception]


class DataSent(bytes, Event):
    ...


class DataReceived(bytes, Event):
    ...


@dataclass
class CommandSent(Event):
    command: Command


@dataclass
class ResponseReceived(Event):
    sequence_number: int
    response: Response
    command_class: Optional[Type[Command]]


@dataclass
class StateUpdated(Event):
    values: Values
