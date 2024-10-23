import pytest

from local_tuya.tuya.events import TuyaCommandSent
from local_tuya.tuya.message import UpdateCommand
from local_tuya.tuya.protocol import TuyaProtocol


class TestProtocol:
    @pytest.fixture
    def transport(self, mocker):
        return mocker.Mock()

    @pytest.fixture
    def protocol(self, transport, notifier):
        return TuyaProtocol(notifier, transport)

    async def test_update(self, protocol, assert_event_emitted):
        await protocol.update({"1": 1})
        assert_event_emitted(TuyaCommandSent(UpdateCommand({"1": 1})), 1)
