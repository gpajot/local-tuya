import asyncio.transports
import sys

import pytest

from local_tuya.backoff import Backoff
from local_tuya.protocol.events import (
    ConnectionEstablished,
    ConnectionLost,
    DataReceived,
    DataSent,
)
from local_tuya.protocol.transport import Transport


class TestTransport:
    @pytest.fixture()
    def backoff(self, mocker):
        return mocker.MagicMock(spec=Backoff)

    @pytest.fixture()
    def transport(self, backoff, notifier):
        return Transport("address", 6666, backoff, notifier)

    @pytest.fixture()
    def transport_future(self):
        return asyncio.Future()

    @pytest.fixture()
    def mock_transport(self, mocker, transport, transport_future):
        mock = mocker.Mock(spec=asyncio.transports.WriteTransport)

        if sys.version_info < (3, 8):
            mocker.patch.object(
                transport, "_get_transport", return_value=transport_future
            )
        else:

            async def _get_transport():
                return await transport_future

            mocker.patch.object(transport, "_get_transport", new=_get_transport)
        mock.close.side_effect = lambda: transport._closed.set()
        return mock

    @pytest.fixture()
    def connected_transport(self, transport, mock_transport, transport_future):
        transport_future.set_result(mock_transport)
        return transport

    @pytest.mark.usefixtures("transport")
    async def test_write_disconnected(self, notifier):
        with pytest.raises(RuntimeError, match="transport is closed"):
            await notifier.emit(DataSent(b""))

    async def test_write_connected(self, connected_transport, notifier, mock_transport):
        async with connected_transport:
            await notifier.emit(DataSent(b"\x00"))
        mock_transport.write.assert_called_once_with(b"\x00")

    async def test_write_connecting(
        self, notifier, transport, mock_transport, transport_future
    ):
        connect_task = asyncio.create_task(transport.__aenter__())
        send_task = asyncio.create_task(notifier.emit(DataSent(b"\x00")))
        await asyncio.sleep(0.001)  # context switch.
        mock_transport.write.assert_not_called()
        transport_future.set_result(mock_transport)
        await asyncio.sleep(0.001)  # context switch.
        mock_transport.write.assert_called_once_with(b"\x00")
        # Cleanup.
        await connect_task
        async with transport:
            await send_task

    async def test_receive(self, notifier, connected_transport, assert_event_emitted):
        async with connected_transport:
            connected_transport.data_received(b"\x00")
            await asyncio.sleep(0)  # context switch.
            assert_event_emitted(DataReceived(b"\x00"), 1)

    async def test_reconnect(self, connected_transport, assert_event_emitted):
        async with connected_transport:
            assert_event_emitted(ConnectionEstablished(), 1)
            error = ConnectionResetError()
            connected_transport.connection_lost(error)
            await asyncio.sleep(0)  # context switch.
            assert_event_emitted(ConnectionLost(error), 1)
            assert_event_emitted(ConnectionEstablished(), 2)
