import asyncio
from contextlib import AbstractContextManager
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


class SequenceBackoff(AbstractContextManager):
    """Backoff according to a wait sequence.
    When it reaches the end of the sequence, it will keep using the last value.

    >>> with SequenceBackoff(1, 5, 10) as backoff:
    >>>     ...
    >>>     await backoff.wait()
    """

    def __init__(self, *sequence: float):
        self.__seq = tuple(sequence)
        self.__index = 0

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.reset()

    def reset(self) -> None:
        self.__index = 0

    async def wait(self) -> None:
        await asyncio.sleep(self.__seq[self.__index])
        if self.__index < len(self.__seq) - 1:
            self.__index += 1

    def __repr__(self) -> str:
        return f"SequenceBackoff({', '.join(map(str, self.__seq))})"

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            lambda e: cls(*e),
            handler(tuple[float, ...]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls._serialize
            ),
        )

    def _serialize(self) -> tuple[float, ...]:
        return self.__seq
