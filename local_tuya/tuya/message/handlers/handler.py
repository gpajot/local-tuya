from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Self

from local_tuya.tuya.config import TuyaConfig
from local_tuya.tuya.message.messages import Command, Response


class MessageHandler(ABC):
    @classmethod
    @abstractmethod
    def from_config(cls, config: TuyaConfig) -> Self | None:
        """Create the handler if it supports the device."""

    @abstractmethod
    def pack(self, sequence_number: int, command: Command) -> bytes:
        """Pack a message into bytes."""

    @abstractmethod
    async def unpack(
        self,
        read: Callable[[int], Awaitable[bytes]],
    ) -> tuple[int, Response, type[Command] | None]:
        """Extract message from the bytes received, also return unused remaining bytes."""
