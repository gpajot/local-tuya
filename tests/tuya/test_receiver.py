import pytest

from local_tuya.tuya.events import (
    TuyaDataReceived,
    TuyaResponseReceived,
)
from local_tuya.tuya.message import MessageHandler, UpdateCommand, UpdateResponse
from local_tuya.tuya.receiver import Receiver


@pytest.fixture
def msg_handler(mocker):
    return mocker.Mock(spec=MessageHandler)


@pytest.fixture(autouse=True)
def receiver(msg_handler, notifier):
    return Receiver("test", msg_handler, notifier)


async def test_no_response(msg_handler, notifier, assert_event_emitted):
    msg_handler.unpack.side_effect = lambda d: (0, None, None, d)
    await notifier.emit(TuyaDataReceived(b"\x00"))
    msg_handler.unpack.side_effect = lambda d: (0, None, None, b"")
    await notifier.emit(TuyaDataReceived(b"\x01"))

    def _raise(data: bytes):
        raise ValueError(data.decode("utf-8"))

    msg_handler.unpack.side_effect = _raise
    with pytest.raises(ValueError, match=b"\x04".decode("utf-8")):
        await notifier.emit(TuyaDataReceived(b"\x04"))

    assert_event_emitted(TuyaResponseReceived(1, UpdateResponse(), UpdateCommand), 0)


async def test_response(msg_handler, notifier, assert_event_emitted):
    msg_handler.unpack.return_value = (1, UpdateResponse(), UpdateCommand, b"")
    await notifier.emit(TuyaDataReceived(b"\x00"))
    assert_event_emitted(TuyaResponseReceived(1, UpdateResponse(), UpdateCommand), 1)
