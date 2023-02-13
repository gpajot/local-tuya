"""Utilities to alter how device values are reported."""

import time
from typing import Callable, Optional, Tuple, TypeVar

T = TypeVar("T")

ValuePreprocessor = Callable[[T], T]


def compose(*preprocessors: ValuePreprocessor[T]) -> ValuePreprocessor[T]:
    """Compose multiple preprocessors.
    They are applied in the order in which they are passed.

    Ex:
    >>> compose(moving_average(5), debounce(30))
    """

    def _wrapper(value: T) -> T:
        for preprocessor in preprocessors:
            value = preprocessor(value)
        return value

    return _wrapper


def moving_average(n: int) -> ValuePreprocessor[float]:
    """Return the moving average over the last n values."""
    values: Tuple[float, ...] = ()

    def _wrapper(value: float) -> float:
        nonlocal values
        values = (*values[1 - n :], value)
        return sum(values) / len(values)

    return _wrapper


def debounce(s: float) -> ValuePreprocessor[float]:
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
