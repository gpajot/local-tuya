from abc import ABC, abstractmethod
from enum import Enum

from local_tuya.protocol import Values


class DataPoint(str, Enum):
    """Data points supported by the device."""


class State(ABC):
    """Typed and user-friendly wrapper around state of the device.
    Prefer using dataclasses or anything generating a proper __repr__ method for debugging.

    Usage:
    >>> from dataclasses import dataclass
    >>>
    >>> @dataclass
    >>> class SwitchState(State):
    >>>     power: bool
    >>>
    >>>     @classmethod
    >>>     def load(cls, values: Values) -> "SwitchState":
    >>>         return cls(power=bool(values[SwitchDataPoint.POWER]))
    """

    @classmethod
    @abstractmethod
    def load(cls, values: Values) -> "State":
        """Create from raw values."""
