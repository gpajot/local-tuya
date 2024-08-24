import pytest

from local_tuya.protocol.events import CommandSent
from local_tuya.protocol.message import UpdateCommand
from local_tuya.protocol.protocol import Protocol


class TestProtocol:
    @pytest.fixture
    def transport(self, mocker):
        return mocker.Mock()

    @pytest.fixture
    def protocol(self, transport, notifier):
        return Protocol(notifier, transport)

    async def test_update(self, protocol, assert_event_emitted):
        await protocol.update({"1": 1})
        assert_event_emitted(CommandSent(UpdateCommand({"1": 1})), 1)
