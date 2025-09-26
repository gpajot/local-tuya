import asyncio.transports

import pytest

from local_tuya.backoff import SequenceBackoff
from local_tuya.tuya.events import (
    TuyaDataReceived,
    TuyaDataSent,
)
from local_tuya.tuya.transport import Transport, TuyaStream


class TestTransport:
    @pytest.fixture
    def backoff(self, mocker):
        return mocker.MagicMock(spec=SequenceBackoff)

    @pytest.fixture
    def reader(self, mocker):
        return mocker.Mock(spec=asyncio.StreamReader)

    @pytest.fixture
    def stream(self, mocker, reader):
        cls = mocker.patch("local_tuya.tuya.transport.TuyaStream")
        s = mocker.MagicMock(spec=TuyaStream)
        s.reader = reader
        cls.return_value = s
        return s

    @pytest.fixture
    async def transport(self, backoff, notifier, stream):
        return Transport(
            name="test",
            address="address",
            port=6666,
            separator=b"z",
            backoff=backoff,
            timeout=5,
            event_notifier=notifier,
        )

    async def test_write(self, notifier, transport, stream):
        async with transport:
            await notifier.emit(TuyaDataSent(b"\x00"))
        stream.write.assert_called_once_with(b"\x00")

    async def test_receive(self, notifier, transport, reader, assert_event_emitted):
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
        assert_event_emitted(TuyaDataReceived(b"\x00z"), 1)
