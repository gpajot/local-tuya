from dataclasses import dataclass
from typing import Union

from typing_extensions import Optional, Protocol

from local_tuya.errors import DecodeResponseError, ResponseError
from local_tuya.protocol import Value, Values

Payload = dict[str, Union[Value, Values]]


class Command(Protocol):
    @property
    def payload(self) -> Optional[Payload]:
        return None


class Response(Protocol):
    @property
    def error(self) -> Optional[ResponseError]:
        return None


class EmptyCommand:
    @property
    def payload(self) -> Optional[Payload]:
        return None


@dataclass
class EmptyResponse:
    _error: Optional[ResponseError] = None

    @property
    def error(self) -> Optional[ResponseError]:
        return self._error


class HeartbeatCommand(EmptyCommand): ...


class HeartbeatResponse(EmptyResponse): ...


class StatusResponse:
    def __init__(
        self,
        payload: Optional[Payload] = None,
        error: Optional[ResponseError] = None,
    ):
        self.error = error
        self.values: Values = {}
        if payload and "dps" in payload and isinstance(payload["dps"], dict):
            self.values = payload["dps"]
        if not self.values and not self.error:
            self.error = DecodeResponseError("no dps in response")


class StateCommand(EmptyCommand): ...


class StateResponse(StatusResponse): ...


@dataclass
class UpdateCommand:
    values: Values

    @property
    def payload(self) -> Payload:
        return {"dps": self.values}


class UpdateResponse(EmptyResponse): ...
