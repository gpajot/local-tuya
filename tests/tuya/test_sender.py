import asyncio

import pytest

from local_tuya.errors import CommandTimeoutError, ResponseError
from local_tuya.tuya.events import (
    TuyaCommandSent,
    TuyaConnectionClosed,
    TuyaDataSent,
    TuyaResponseReceived,
)
from local_tuya.tuya.message import (
    HeartbeatCommand,
    HeartbeatResponse,
    MessageHandler,
    StateCommand,
    UpdateCommand,
)
from local_tuya.tuya.sender import Sender


@pytest.fixture
def msg_handler(mocker):
    handler = mocker.Mock(spec=MessageHandler)
    handler.pack.return_value = b"\x00"
    return handler


@pytest.fixture
def sender(msg_handler, notifier):
    with Sender("test", msg_handler, notifier, 0.01) as s:
        yield s


@pytest.fixture
def command_sent():
    return TuyaCommandSent(HeartbeatCommand())


def test_sequence_number(sender):
    assert sender._get_sequence_number(StateCommand()) == 1
    assert sender._get_sequence_number(HeartbeatCommand()) == 0
    assert sender._get_sequence_number(UpdateCommand({})) == 2


async def test_send(sender, notifier, command_sent, assert_event_emitted):
    with pytest.raises(CommandTimeoutError):
        await notifier.emit(command_sent)
    assert_event_emitted(TuyaDataSent(b"\x00"), 1)


async def test_reconnect(sender, notifier, command_sent, assert_event_emitted):
    task = asyncio.create_task(notifier.emit(command_sent))
    await asyncio.sleep(0)  # Context switch.
    await notifier.emit(TuyaConnectionClosed(ConnectionError("failed")))
    with pytest.raises(ConnectionError, match="failed"):
        await task
    assert_event_emitted(TuyaDataSent(b"\x00"), 1)


async def test_response_success(sender, notifier, command_sent):
    task = asyncio.create_task(notifier.emit(command_sent))
    await asyncio.sleep(0)  # context switch
    await notifier.emit(TuyaResponseReceived(0, HeartbeatResponse(), HeartbeatCommand))
    await task


async def test_response_failure(sender, notifier, command_sent):
    task = asyncio.create_task(notifier.emit(command_sent))
    await asyncio.sleep(0)  # context switch
    await notifier.emit(
        TuyaResponseReceived(0, HeartbeatResponse(ResponseError()), HeartbeatCommand)
    )
    with pytest.raises(ResponseError):
        await task
