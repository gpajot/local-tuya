import asyncio
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager


class Backoff(AbstractContextManager, ABC):
    """Can be used to wait according to a strategy until exited."""

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.reset()

    @abstractmethod
    async def wait(self) -> None:
        """Wait according to the backoff strategy."""

    @abstractmethod
    def reset(self) -> None:
        """Reset the backoff."""


class SequenceBackoff(Backoff):
    """Backoff according to a wait sequence.
    When it reaches the end of the sequence, it will keep using the last value.

    >>> with Backoff(1, 5, 10) as backoff:
    >>>     ...
    >>>     await backoff.wait()
    """

    def __init__(self, *sequence: float):
        self.__seq = tuple(sequence)
        self.__index = 0

    def reset(self) -> None:
        self.__index = 0

    async def wait(self) -> None:
        await asyncio.sleep(self.__seq[self.__index])
        if self.__index < len(self.__seq) - 1:
            self.__index += 1
