import pytest

from local_tuya.tuya.events import (
    TuyaConnectionClosed,
    TuyaDataReceived,
    TuyaResponseReceived,
)
from local_tuya.tuya.message import MessageHandler, UpdateCommand, UpdateResponse
from local_tuya.tuya.receiver import Receiver


class TestReceiver:
    @pytest.fixture
    def msg_handler(self, mocker):
        return mocker.Mock(spec=MessageHandler)

    @pytest.fixture
    def receiver(self, msg_handler, notifier):
        return Receiver("test", msg_handler, notifier)

    async def test_buffer(self, receiver, msg_handler, notifier):
        msg_handler.unpack.side_effect = lambda d: (0, None, None, d)
        await notifier.emit(TuyaDataReceived(b"\x00"))
        await notifier.emit(TuyaDataReceived(b"\x00"))
        await notifier.emit(TuyaConnectionClosed(None))
        msg_handler.unpack.side_effect = lambda d: (0, None, None, b"")
        await notifier.emit(TuyaDataReceived(b"\x00"))
        await notifier.emit(TuyaDataReceived(b"\x00"))
        msg_handler.unpack.side_effect = ValueError
        await notifier.emit(TuyaDataReceived(b"\x00"))
        await notifier.emit(TuyaDataReceived(b"\x00"))

        assert msg_handler.unpack.call_count == 6
        msg_handler.unpack.assert_has_calls(
            (
                ((b"\x00",), {}),
                ((b"\x00\x00",), {}),
                ((b"\x00",), {}),
                ((b"\x00",), {}),
                ((b"\x00",), {}),
                ((b"\x00",), {}),
            )
        )

    async def test_response_received(
        self, receiver, msg_handler, notifier, assert_event_emitted
    ):
        msg_handler.unpack.return_value = (1, UpdateResponse(), UpdateCommand, b"")
        await notifier.emit(TuyaDataReceived(b"\x00"))
        assert_event_emitted(
            TuyaResponseReceived(1, UpdateResponse(), UpdateCommand), 1
        )
