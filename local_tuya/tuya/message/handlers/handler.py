from abc import ABC, abstractmethod
from typing import ClassVar, Optional

from local_tuya.tuya.config import TuyaConfig
from local_tuya.tuya.message.messages import Command, Response


class MessageHandler(ABC):
    SUFFIX: ClassVar[int]

    @staticmethod
    @abstractmethod
    def from_config(config: TuyaConfig) -> Optional["MessageHandler"]:
        """Create the handler if it supports the device."""

    @abstractmethod
    def pack(self, sequence_number: int, message: Command) -> bytes:
        """Pack a message into bytes."""

    @abstractmethod
    def unpack(
        self, data: bytes
    ) -> tuple[int, Optional[Response], Optional[type[Command]], bytes]:
        """Extract message from the bytes received, also return unused remaining bytes."""
