import asyncio.transports

import pytest

from local_tuya.backoff import SequenceBackoff
from local_tuya.tuya.events import (
    TuyaCommandSent,
    TuyaResponseReceived,
)
from local_tuya.tuya.message import (
    HeartbeatCommand,
    MessageHandler,
    StateCommand,
    UpdateCommand,
    UpdateResponse,
)
from local_tuya.tuya.transport import (
    SequenceNumberGetter,
    Transport,
    TuyaStream,
)


def test_sequence_number():
    seq = SequenceNumberGetter()
    with seq:
        assert seq(StateCommand()) == 1
        assert seq(HeartbeatCommand()) == 0
        assert seq(UpdateCommand({})) == 2
    with seq:
        assert seq(StateCommand()) == 1


@pytest.fixture
def backoff(mocker):
    return mocker.MagicMock(spec=SequenceBackoff)


@pytest.fixture
def reader(mocker):
    return mocker.Mock(spec=asyncio.StreamReader)


@pytest.fixture
def stream(mocker, reader):
    cls = mocker.patch("local_tuya.tuya.transport.TuyaStream")
    s = mocker.MagicMock(spec=TuyaStream)
    s.reader = reader
    cls.return_value = s
    return s


@pytest.fixture
def msg_handler(mocker):
    return mocker.Mock(spec=MessageHandler)


@pytest.fixture
async def transport(backoff, notifier, stream, msg_handler):
    return Transport(
        name="test",
        address="address",
        port=6666,
        backoff=backoff,
        timeout=5,
        keepalive=5,
        message_handler=msg_handler,
        event_notifier=notifier,
    )


async def test_write(notifier, transport, stream, msg_handler):
    msg_handler.pack.return_value = b"\x00"
    cmd = HeartbeatCommand()
    async with transport:
        await notifier.emit(TuyaCommandSent(cmd))
    stream.write.assert_called_once_with(b"\x00")
    msg_handler.pack.assert_called_once_with(0, cmd)


async def test_receive(notifier, transport, reader, assert_event_emitted, msg_handler):
    msg_handler.separator = b"z"
    msg_handler.unpack.return_value = (1, UpdateResponse(), UpdateCommand)
    returned = False

    async def _read(_):
        nonlocal returned
        if not returned:
            returned = True
            return b"\x00z"
        await asyncio.sleep(1)
        return b"\x00z"

    reader.readuntil.side_effect = _read
    async with transport:
        await asyncio.sleep(0)  # context switch.
    msg_handler.unpack.assert_called_once_with(b"\x00z")
    assert_event_emitted(TuyaResponseReceived(1, UpdateResponse(), UpdateCommand), 1)
