import binascii
import json
import logging
import struct
from typing import Callable, ClassVar, Dict, Optional, Tuple, Type

from local_tuya.errors import DecodeResponseError, LocalTuyaError, ResponseError
from local_tuya.protocol.config import ProtocolConfig, Version
from local_tuya.protocol.message.handlers.crypto import AESCipher
from local_tuya.protocol.message.handlers.handler import MessageHandler
from local_tuya.protocol.message.messages import (
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
    COMMANDS: ClassVar[Dict[Type[Command], int]] = {
        UpdateCommand: 7,
        HeartbeatCommand: 9,
        StateCommand: 10,
    }
    RESPONSES: ClassVar[
        Dict[int, Callable[[Optional[Payload], Optional[ResponseError]], Response]]
    ] = {
        7: lambda p, e: UpdateResponse(e),
        8: StatusResponse,
        9: lambda p, e: HeartbeatResponse(e),
        10: StateResponse,
    }
    # Corresponding to responses.
    COMMAND_CLASSES: ClassVar[Dict[int, Type[Command]]] = {
        7: UpdateCommand,
        9: HeartbeatCommand,
        10: StateCommand,
    }

    def __init__(self, config: ProtocolConfig):
        self._cfg = config
        self._cipher = AESCipher(config.key)
        self._version_header = config.version + self.VERSION_HEADER

    @staticmethod
    def from_config(config: ProtocolConfig) -> Optional["MessageHandler"]:
        if config.version is Version.v33:
            return V33MessageHandler(config)

    def pack(self, sequence_number: int, command: Command) -> bytes:
        if type(command) not in self.COMMANDS:
            raise LocalTuyaError(f"unknown command {command}")
        payload = command.payload or {}
        # TODO: check if needed.
        # payload.update({
        #     # "gwId": self._cfg.id,
        #     # "devId": self._cfg.id,
        # })
        # if not isinstance(command, HeartBeatCommand):
        #     payload.update({
        #         # "uid": self._cfg.id,
        #         "t": int(time.time()),
        #     })
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

    def unpack(
        self, data: bytes
    ) -> Tuple[int, Optional[Response], Optional[Type[Command]], bytes]:
        header_length = struct.calcsize(self.HEADER_FMT)

        # Header.
        if len(data) < header_length:
            # Wait for more data.
            return 0, None, None, data
        header = data[:header_length]
        prefix, sequence_number, cmd, payload_length = struct.unpack(
            self.HEADER_FMT, header
        )
        if prefix != self.PREFIX:
            raise ResponseError(f"incorrect prefix: 0x{prefix:08x}")

        # Payload.
        if len(data) < header_length + payload_length:
            # Wait for more data.
            return 0, None, None, data
        payload = data[header_length : header_length + payload_length]

        if cmd not in self.RESPONSES:
            logger.warning("unknown response type %i, ignoring", cmd)
            return 0, None, None, data[header_length + payload_length :]

        response_factory = self.RESPONSES[cmd]
        command_class = self.COMMAND_CLASSES.get(cmd)

        try:
            # Get the return code.
            return_code_length = struct.calcsize(self.RETURN_CODE_FMT)
            (return_code,) = struct.unpack(
                self.RETURN_CODE_FMT, payload[:return_code_length]
            )

            # Check the suffix, ignore the hash.
            end_length = struct.calcsize(self.END_FMT)
            _, suffix = struct.unpack(self.END_FMT, payload[-end_length:])
            if suffix != self.SUFFIX:
                raise ResponseError(f"incorrect suffix: 0x{suffix:08x}")

            # Parse payload.
            payload_content = payload[return_code_length:-end_length]
            if payload_content.startswith(self._cfg.version):
                payload_content = payload_content[len(self._version_header) :]
            parsed_payload: Optional[Payload] = None
            error: Optional[ResponseError] = None
            if return_code:
                # Use the payload content as the error description.
                error = ResponseError(payload_content.decode())
            elif payload_content:
                try:
                    decrypted = self._cipher.decrypt(payload_content)
                    try:
                        parsed_payload = json.loads(decrypted)
                    except Exception as e:
                        error = DecodeResponseError(
                            f"could not load {decrypted!r} as json", e
                        )
                except Exception as e:
                    error = DecodeResponseError(
                        f"could not decrypt {payload_content!r}", e
                    )

            return (
                sequence_number,
                response_factory(parsed_payload, error),
                command_class,
                data[header_length + payload_length :],
            )
        except Exception as e:
            return (
                sequence_number,
                response_factory(None, ResponseError("error handling response", e)),
                command_class,
                data[header_length + payload_length :],
            )
