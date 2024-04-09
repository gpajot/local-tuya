import pytest

from local_tuya.protocol.events import CommandSent, ConnectionBroken, StateUpdated
from local_tuya.protocol.message import UpdateCommand
from local_tuya.protocol.protocol import Protocol


class TestProtocol:
    @pytest.fixture()
    def transport(self, mocker):
        return mocker.patch("local_tuya.protocol.protocol.Transport")

    @pytest.fixture()
    def sender(self, mocker):
        return mocker.patch("local_tuya.protocol.protocol.Sender")

    @pytest.fixture()
    def heartbeat(self, mocker):
        return mocker.patch("local_tuya.protocol.protocol.Heartbeat")

    @pytest.fixture()
    def state(self, mocker):
        return mocker.patch("local_tuya.protocol.protocol.State")

    @pytest.fixture()
    def state_updated_callback(self, mocker):
        return mocker.AsyncMock()

    @pytest.fixture()
    def connection_broken_callback(self, mocker):
        return mocker.AsyncMock()

    @pytest.fixture()
    def config(self, mocker):
        return mocker.Mock()

    @pytest.fixture()
    def protocol(
        self,
        mocker,
        transport,
        sender,
        heartbeat,
        state,
        notifier,
        config,
        state_updated_callback,
        connection_broken_callback,
    ):
        mocker.patch(
            "local_tuya.protocol.protocol.EventNotifier", return_value=notifier
        )
        mocker.patch("local_tuya.protocol.protocol.get_handler")
        return Protocol(
            config,
            state_updated_callback,
            connection_broken_callback,
        )

    @pytest.mark.usefixtures("protocol")
    async def test_state_updated_callback(self, state_updated_callback, notifier):
        await notifier.emit(StateUpdated({"1": 1}))
        state_updated_callback.assert_awaited_with({"1": 1})

    @pytest.mark.usefixtures("protocol")
    async def test_connection_broken_callback(
        self, connection_broken_callback, notifier
    ):
        await notifier.emit(ConnectionBroken())
        connection_broken_callback.assert_awaited_once()

    async def test_update(self, protocol, config, assert_event_emitted):
        await protocol.update({"1": 1})
        assert_event_emitted(CommandSent(UpdateCommand({"1": 1})), 1)
