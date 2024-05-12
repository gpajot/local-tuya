import asyncio

import pytest

from local_tuya.protocol.events import (
    CommandSent,
    ConnectionClosed,
    ConnectionEstablished,
    ResponseReceived,
    StateUpdated,
)
from local_tuya.protocol.message import StateCommand, StateResponse, StatusResponse
from local_tuya.protocol.state import State


class TestState:
    @pytest.fixture()
    def state(self, notifier):
        return State(0.01, notifier)

    async def test_connection_lifecycle(
        self, state, notifier, notifier_spy, assert_event_emitted
    ):
        with state:
            await asyncio.sleep(0.015)
            notifier_spy.assert_not_called()
            await notifier.emit(ConnectionEstablished())
            await asyncio.sleep(0.005)
            assert_event_emitted(CommandSent(StateCommand()), 1)
            await notifier.emit(ConnectionClosed(None))
            notifier_spy.reset_mock()
            await asyncio.sleep(0.015)
            notifier_spy.assert_not_called()

    @pytest.mark.usefixtures("state")
    async def test_updates(self, notifier, notifier_spy, assert_event_emitted):
        await notifier.emit(ResponseReceived(0, StateResponse({"1": 1, "2": 1}), None))
        # Wrong to_xml_dict, should not fail.
        assert_event_emitted(StateUpdated({"1": 1, "2": 1}), 0)
        await notifier.emit(
            ResponseReceived(0, StateResponse({"dps": {"1": 1, "2": 1}}), None)
        )
        assert_event_emitted(StateUpdated({"1": 1, "2": 1}), 1)
        await notifier.emit(
            ResponseReceived(0, StatusResponse({"dps": {"2": 2}}), None)
        )
        assert_event_emitted(StateUpdated({"1": 1, "2": 2}), 1)
