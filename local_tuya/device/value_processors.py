"""Utilities to alter how device values are reported."""

import time
from typing import Callable, Optional, TypeVar

T = TypeVar("T")

ValueProcessor = Callable[[T], T]


def compose(*processors: ValueProcessor[T]) -> ValueProcessor[T]:
    """Compose multiple processors.
    They are applied in the order in which they are passed.

    Ex:
    >>> compose(moving_average(5), debounce(30))
    """

    def _wrapper(value: T) -> T:
        for processor in processors:
            value = processor(value)
        return value

    return _wrapper


def moving_average(n: int) -> ValueProcessor[float]:
    """Return the moving average over the last n values."""
    values: tuple[float, ...] = ()

    def _wrapper(value: float) -> float:
        nonlocal values
        values = (*values[1 - n :], value)
        return sum(values) / len(values)

    return _wrapper


def debounce(s: float) -> ValueProcessor[float]:
    """Debounce the updates and return the first value within a period of s seconds."""
    last: Optional[float] = None
    last_time: float = 0

    def _wrapper(value: float) -> float:
        nonlocal last, last_time
        now = time.monotonic()
        if last is None or now >= last_time + s:
            last = value
            last_time = now
        return last

    return _wrapper


def round_(n: int) -> ValueProcessor[float]:
    """Round to n decimals."""

    def _wrapper(value: float) -> float:
        return round(value, n)

    return _wrapper
