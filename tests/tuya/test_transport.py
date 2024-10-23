import asyncio.transports

import pytest

from local_tuya.backoff import Backoff
from local_tuya.tuya.events import (
    TuyaConnectionClosed,
    TuyaConnectionEstablished,
    TuyaDataReceived,
    TuyaDataSent,
    TuyaResponseReceived,
)
from local_tuya.tuya.message.messages import EmptyResponse
from local_tuya.tuya.transport import Transport


class TestTransport:
    @pytest.fixture
    def backoff(self, mocker):
        return mocker.MagicMock(spec=Backoff)

    @pytest.fixture
    async def transport(self, backoff, notifier):
        return Transport(
            name="test",
            address="address",
            port=6666,
            backoff=backoff,
            timeout=5,
            event_notifier=notifier,
        )

    @pytest.fixture
    async def transport_future(self):
        return asyncio.Future()

    @pytest.fixture
    def mock_transport(self, mocker, transport, transport_future):
        mock = mocker.Mock(spec=asyncio.transports.WriteTransport)

        async def _get_transport():
            return await transport_future

        mocker.patch.object(transport, "_get_transport", new=_get_transport)
        mock.close.side_effect = lambda: transport._closed.set()
        return mock

    @pytest.fixture
    async def connected_transport(
        self,
        transport,
        mock_transport,
        transport_future,
        notifier_spy,  # To spy the connection established event.
    ):
        transport_future.set_result(mock_transport)
        async with transport:
            await transport._connected.wait()
            yield transport

    @pytest.mark.usefixtures("transport")
    async def test_write_disconnected(self, notifier):
        with pytest.raises(RuntimeError, match="transport is closed"):
            await notifier.emit(TuyaDataSent(b""))

    async def test_write_connected(self, connected_transport, notifier, mock_transport):
        await notifier.emit(TuyaDataSent(b"\x00"))
        mock_transport.write.assert_called_once_with(b"\x00")

    async def test_write_connecting(
        self, notifier, transport, mock_transport, transport_future
    ):
        async with transport:
            send_task = asyncio.create_task(notifier.emit(TuyaDataSent(b"\x00")))
            await asyncio.sleep(0.001)  # context switch.
            mock_transport.write.assert_not_called()
            transport_future.set_result(mock_transport)
            await asyncio.sleep(0.001)  # context switch.
            mock_transport.write.assert_called_once_with(b"\x00")
            # Cleanup.
            await send_task

    async def test_receive(self, notifier, connected_transport, assert_event_emitted):
        connected_transport.data_received(b"\x00")
        await asyncio.sleep(0)  # context switch.
        assert_event_emitted(TuyaDataReceived(b"\x00"), 1)

    async def test_reconnect(
        self, connected_transport, assert_event_emitted, backoff, notifier
    ):
        assert_event_emitted(TuyaConnectionEstablished(), 1)
        error = ConnectionResetError()
        connected_transport.connection_lost(error)
        await asyncio.sleep(0)  # context switch.
        assert_event_emitted(TuyaConnectionClosed(error), 1)
        assert_event_emitted(TuyaConnectionEstablished(), 2)
        assert backoff.wait.call_count == 2
        backoff.reset.assert_not_called()
        await notifier.emit(TuyaResponseReceived(0, EmptyResponse(), None))
        backoff.reset.assert_called_once()
