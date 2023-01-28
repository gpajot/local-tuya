from typing import Optional


class LocalTuyaError(Exception):
    """Generic local Tuya error."""


class CommandTimeoutError(LocalTuyaError):
    """The device failed to send a response within the time allowed."""


class ResponseError(LocalTuyaError):
    """Generic error in responses"""

    def __init__(self, message: str = "", cause: Optional[Exception] = None):
        super().__init__(message)
        if cause:
            self.__cause__ = cause


class DecodeResponseError(ResponseError):
    """Error parsing Tuya response."""
