import asyncio.transports
import inspect

import pytest

from local_tuya.backoff import Backoff
from local_tuya.protocol.events import (
    ConnectionClosed,
    ConnectionEstablished,
    DataReceived,
    DataSent,
    ResponseReceived,
)
from local_tuya.protocol.message.messages import EmptyResponse
from local_tuya.protocol.transport import Transport, _get_host


class TestTransport:
    @pytest.fixture()
    def backoff(self, mocker):
        return mocker.MagicMock(spec=Backoff)

    @pytest.fixture()
    def transport(self, backoff, notifier):
        return Transport(
            address="address",
            port=6666,
            backoff=backoff,
            timeout=5,
            event_notifier=notifier,
        )

    @pytest.fixture()
    def transport_future(self):
        return asyncio.Future()

    @pytest.fixture()
    def mock_transport(self, mocker, transport, transport_future):
        mock = mocker.Mock(spec=asyncio.transports.WriteTransport)

        async def _get_transport():
            return await transport_future

        mocker.patch.object(transport, "_get_transport", new=_get_transport)
        mock.close.side_effect = lambda: transport._closed.set()
        return mock

    @pytest.fixture()
    async def connected_transport(
        self,
        transport,
        mock_transport,
        transport_future,
        notifier_spy,  # To spy the connection established event.
    ):
        transport_future.set_result(mock_transport)
        async with transport:
            await transport.connect()
            yield transport

    @pytest.mark.usefixtures("transport")
    async def test_write_disconnected(self, notifier):
        with pytest.raises(RuntimeError, match="transport is closed"):
            await notifier.emit(DataSent(b""))

    async def test_write_connected(self, connected_transport, notifier, mock_transport):
        await notifier.emit(DataSent(b"\x00"))
        mock_transport.write.assert_called_once_with(b"\x00")

    async def test_write_connecting(
        self, notifier, transport, mock_transport, transport_future
    ):
        transport.connect()
        send_task = asyncio.create_task(notifier.emit(DataSent(b"\x00")))
        await asyncio.sleep(0.001)  # context switch.
        mock_transport.write.assert_not_called()
        transport_future.set_result(mock_transport)
        await asyncio.sleep(0.001)  # context switch.
        mock_transport.write.assert_called_once_with(b"\x00")
        # Cleanup.
        async with transport:
            await send_task

    async def test_receive(self, notifier, connected_transport, assert_event_emitted):
        connected_transport.data_received(b"\x00")
        await asyncio.sleep(0)  # context switch.
        assert_event_emitted(DataReceived(b"\x00"), 1)

    async def test_reconnect(
        self, connected_transport, assert_event_emitted, backoff, notifier
    ):
        assert_event_emitted(ConnectionEstablished(), 1)
        error = ConnectionResetError()
        connected_transport.connection_lost(error)
        await asyncio.sleep(0)  # context switch.
        assert_event_emitted(ConnectionClosed(error), 1)
        assert_event_emitted(ConnectionEstablished(), 2)
        assert backoff.wait.call_count == 2
        backoff.reset.assert_not_called()
        await notifier.emit(ResponseReceived(0, EmptyResponse(), None))
        backoff.reset.assert_called_once()


@pytest.mark.parametrize(
    ("address", "mock_stdout", "expected"),
    [
        ("192.168.1.2", b"", "192.168.1.2"),
        ("f6:bc:2e:be:de:44", b"", ValueError),
        ("f6:bc:2e:be:de:44", b"192.168.1.2\n", "192.168.1.2"),
        ("something-else", b"", "something-else"),
    ],
)
async def test_get_host(address, mock_stdout, expected, mocker):
    create_subprocess_mock = mocker.patch("asyncio.create_subprocess_shell")
    create_subprocess_mock.return_value.communicate.return_value = (mock_stdout, "")
    if inspect.isclass(expected) and issubclass(expected, Exception):
        with pytest.raises(expected):
            await _get_host(address)
    else:
        assert await _get_host(address) == expected
