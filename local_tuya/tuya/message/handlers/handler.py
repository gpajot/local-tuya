from abc import ABC, abstractmethod
from typing import ClassVar, Self

from local_tuya.tuya.config import TuyaConfig
from local_tuya.tuya.message.messages import Command, Response


class MessageHandler(ABC):
    SUFFIX: ClassVar[int]

    @classmethod
    @abstractmethod
    def from_config(cls, config: TuyaConfig) -> Self | None:
        """Create the handler if it supports the device."""

    @abstractmethod
    def pack(self, sequence_number: int, message: Command) -> bytes:
        """Pack a message into bytes."""

    @abstractmethod
    def unpack(
        self, data: bytes
    ) -> tuple[int, Response | None, type[Command] | None, bytes]:
        """Extract message from the bytes received, also return unused remaining bytes."""
