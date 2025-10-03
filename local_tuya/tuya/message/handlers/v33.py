import binascii
import json
import logging
import struct
from typing import Callable, ClassVar, Self

from local_tuya.errors import DecodeResponseError, LocalTuyaError, ResponseError
from local_tuya.tuya.config import TuyaConfig, TuyaVersion
from local_tuya.tuya.message.handlers.crypto import AESCipher
from local_tuya.tuya.message.handlers.handler import MessageHandler
from local_tuya.tuya.message.messages import (
    Command,
    HeartbeatCommand,
    HeartbeatResponse,
    Payload,
    Response,
    StateCommand,
    StateResponse,
    StatusResponse,
    UpdateCommand,
    UpdateResponse,
)

logger = logging.getLogger(__name__)


class V33MessageHandler(MessageHandler):
    PREFIX: ClassVar[int] = 0x000055AA
    SUFFIX: ClassVar[int] = 0x0000AA55
    VERSION_HEADER: ClassVar[bytes] = 12 * b"\x00"

    # Prefix + sequence num + command + payload length.
    HEADER_FMT: ClassVar[str] = ">4I"
    RETURN_CODE_FMT: ClassVar[str] = ">I"
    # Hash + suffix.
    END_FMT: ClassVar[str] = ">2I"

    # Messages.
    COMMANDS: ClassVar[dict[type[Command], int]] = {
        UpdateCommand: 7,
        HeartbeatCommand: 9,
        StateCommand: 10,
    }
    RESPONSES: ClassVar[
        dict[int, Callable[[Payload | None, ResponseError | None], Response]]
    ] = {
        7: lambda p, e: UpdateResponse(e),
        8: StatusResponse,
        9: lambda p, e: HeartbeatResponse(e),
        10: StateResponse,
    }
    # Corresponding to responses.
    COMMAND_CLASSES: ClassVar[dict[int, type[Command]]] = {
        7: UpdateCommand,
        9: HeartbeatCommand,
        10: StateCommand,
    }

    def __init__(self, config: TuyaConfig):
        self._cfg = config
        self._cipher = AESCipher(config.key)
        self._version_header = config.version + self.VERSION_HEADER

    @property
    def separator(self) -> bytes:
        return self.SUFFIX.to_bytes(length=4, byteorder="big")

    @classmethod
    def from_config(cls, config: TuyaConfig) -> Self | None:
        if config.version is TuyaVersion.v33:
            return cls(config)
        return None

    def pack(self, sequence_number: int, command: Command) -> bytes:
        if type(command) not in self.COMMANDS:
            raise LocalTuyaError(f"unknown command {command}")
        payload = command.payload or {}
        encrypted = self._cipher.encrypt(
            json.dumps(payload, separators=(",", ":")).encode()
        )
        if isinstance(command, UpdateCommand):
            full_payload = self._version_header + encrypted
        else:
            full_payload = encrypted

        data = (
            struct.pack(
                self.HEADER_FMT,
                self.PREFIX,
                sequence_number,
                self.COMMANDS[type(command)],
                len(full_payload) + struct.calcsize(self.END_FMT),
            )
            + full_payload
        )
        data += struct.pack(
            self.END_FMT,
            binascii.crc32(data) & 0xFFFFFFFF,
            self.SUFFIX,
        )
        return data

    def unpack(self, data: bytes) -> tuple[int, Response, type[Command] | None]:
        header_length = struct.calcsize(self.HEADER_FMT)

        # Header.
        if len(data) < header_length:
            raise DecodeResponseError(f"not enough data: {data!r}")
        header = data[:header_length]
        prefix, sequence_number, cmd, payload_length = struct.unpack(
            self.HEADER_FMT, header
        )
        if prefix != self.PREFIX:
            raise DecodeResponseError(f"incorrect prefix: 0x{prefix:08x}")
        if cmd not in self.RESPONSES:
            raise DecodeResponseError(f"unknown response type 0x{cmd:08x}")
        response_factory = self.RESPONSES[cmd]
        command_class = self.COMMAND_CLASSES.get(cmd)

        # Check length.
        return_code_length = struct.calcsize(self.RETURN_CODE_FMT)
        end_length = struct.calcsize(self.END_FMT)
        if payload_length < return_code_length + end_length:
            raise DecodeResponseError(f"payload not long enough: {data!r}")
        elif len(data) < header_length + payload_length:
            raise DecodeResponseError(f"not enough data: {data!r}")
        elif len(data) > header_length + payload_length:
            raise DecodeResponseError(f"too much data: {data!r}")

        # Check the suffix, ignore the hash.
        _, suffix = struct.unpack(self.END_FMT, data[-end_length:])
        if suffix != self.SUFFIX:
            raise DecodeResponseError(f"incorrect suffix: 0x{suffix:08x}")

        # Get the return code.
        (return_code,) = struct.unpack(
            self.RETURN_CODE_FMT,
            data[header_length : header_length + return_code_length],
        )

        payload_content = data[header_length + return_code_length : -end_length]
        if payload_content.startswith(self._cfg.version):
            payload_content = payload_content[len(self._version_header) :]

        # Parse payload.
        parsed_payload: Payload | None = None
        error: ResponseError | None = None
        if return_code:
            error = ResponseError(f"error from device: {payload_content!r}")
        elif payload_content:
            try:
                decrypted = self._cipher.decrypt(payload_content)
            except Exception as e:
                raise DecodeResponseError(
                    f"could not decrypt {payload_content!r}"
                ) from e
            try:
                parsed_payload = json.loads(decrypted)
            except Exception as e:
                raise DecodeResponseError(
                    f"could not load {decrypted!r} as json"
                ) from e

        return (
            sequence_number,
            response_factory(parsed_payload, error),
            command_class,
        )
