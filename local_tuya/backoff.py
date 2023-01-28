import asyncio
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager


class Backoff(AbstractContextManager, ABC):
    """Can be used to wait according to a strategy until exited."""

    @abstractmethod
    async def __call__(self) -> None:
        """Wait according to the backoff strategy."""


class SequenceBackoff(Backoff):
    """Backoff according to a wait sequence.
    When it reaches the end of the sequence, it will keep using the last value.

    >>> with Backoff(1, 5, 10) as backoff:
    >>>     ...
    >>>     await backoff()
    """

    def __init__(self, *sequence: float):
        self.__seq = tuple(sequence)
        self.__index = 0

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.__index = 0

    async def __call__(self) -> None:
        await asyncio.sleep(self.__seq[self.__index])
        if self.__index < len(self.__seq) - 1:
            self.__index += 1
