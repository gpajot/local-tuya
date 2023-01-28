import asyncio

import pytest
import pytest_asyncio

from local_tuya.errors import CommandTimeoutError, ResponseError
from local_tuya.protocol.events import (
    CommandSent,
    ConnectionEstablished,
    ConnectionLost,
    DataSent,
    ResponseReceived,
)
from local_tuya.protocol.message import (
    HeartbeatCommand,
    HeartbeatResponse,
    MessageHandler,
    StateCommand,
    UpdateCommand,
)
from local_tuya.protocol.sender import Sender


class TestSender:
    @pytest.fixture()
    def msg_handler(self, mocker):
        handler = mocker.Mock(spec=MessageHandler)
        handler.pack.return_value = b"\x00"
        return handler

    @pytest_asyncio.fixture()
    async def sender(self, msg_handler, notifier):
        async with Sender(msg_handler, notifier, 0.01) as sender:
            yield sender

    @pytest.fixture()
    def command_sent(self):
        return CommandSent(HeartbeatCommand())

    def test_sequence_number(self, sender):
        assert sender._get_sequence_number(StateCommand()) == 1
        assert sender._get_sequence_number(HeartbeatCommand()) == 0
        assert sender._get_sequence_number(UpdateCommand({})) == 2

    async def test_send_with_connection(
        self, sender, notifier, command_sent, assert_event_emitted
    ):
        await notifier.emit(ConnectionEstablished())
        task = asyncio.create_task(notifier.emit(command_sent))
        await asyncio.sleep(0.001)  # context switch
        assert_event_emitted(DataSent(b"\x00"), 1)
        task.cancel()

    async def test_send_no_connection(
        self, sender, notifier, command_sent, assert_event_emitted
    ):
        task = asyncio.create_task(notifier.emit(command_sent))
        await asyncio.sleep(0.001)  # context switch
        assert_event_emitted(DataSent(b"\x00"), 0)
        task.cancel()

    async def test_reconnect(
        self, sender, notifier, command_sent, assert_event_emitted
    ):
        await notifier.emit(ConnectionEstablished())
        task = asyncio.create_task(notifier.emit(command_sent))
        await asyncio.sleep(0.001)  # context switch
        await notifier.emit(ConnectionLost(None))
        await asyncio.sleep(0.015)
        await notifier.emit(ConnectionEstablished())
        await asyncio.sleep(0.001)  # context switch
        # Sending should be paused and resumed.
        assert_event_emitted(DataSent(b"\x00"), 2)
        task.cancel()

    async def test_timeout(self, sender, notifier, command_sent):
        await notifier.emit(ConnectionEstablished())
        with pytest.raises(CommandTimeoutError):
            await notifier.emit(command_sent)

    async def test_response_success(self, sender, notifier, command_sent):
        await notifier.emit(ConnectionEstablished())
        task = asyncio.create_task(notifier.emit(command_sent))
        await asyncio.sleep(0.001)  # context switch
        await notifier.emit(ResponseReceived(0, HeartbeatResponse(), HeartbeatCommand))
        await task

    async def test_response_failure(self, sender, notifier, command_sent):
        await notifier.emit(ConnectionEstablished())
        task = asyncio.create_task(notifier.emit(command_sent))
        await asyncio.sleep(0.001)  # context switch
        await notifier.emit(
            ResponseReceived(0, HeartbeatResponse(ResponseError()), HeartbeatCommand)
        )
        with pytest.raises(ResponseError):
            await task
