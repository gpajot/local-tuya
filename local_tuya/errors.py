class LocalTuyaError(Exception):
    """Generic local Tuya error."""


class CommandTimeoutError(LocalTuyaError):
    """The device failed to send a response within the time allowed."""


class ResponseError(LocalTuyaError):
    """Error from Tuya device."""


class DecodeResponseError(LocalTuyaError):
    """Error parsing Tuya response."""
