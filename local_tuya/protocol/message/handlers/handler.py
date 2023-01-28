from abc import ABC, abstractmethod
from typing import Optional, Tuple, Type

from local_tuya.protocol.config import ProtocolConfig
from local_tuya.protocol.message.messages import Command, Response


class MessageHandler(ABC):
    @staticmethod
    @abstractmethod
    def from_config(config: ProtocolConfig) -> Optional["MessageHandler"]:
        """Create the handler if it supports the device."""

    @abstractmethod
    def pack(self, sequence_number: int, message: Command) -> bytes:
        """Pack a message into bytes."""

    @abstractmethod
    def unpack(
        self, data: bytes
    ) -> Tuple[int, Optional[Response], Optional[Type[Command]], bytes]:
        """Extract message from the bytes received, also return unused remaining bytes."""
