class LocalTuyaError(Exception):
    """Generic local Tuya error."""


class ResponseError(LocalTuyaError):
    """Error from Tuya device."""


class DecodeResponseError(LocalTuyaError):
    """Error parsing Tuya response."""
