import asyncio

import pytest

from local_tuya.tuya.events import (
    TuyaCommandSent,
    TuyaConnectionClosed,
    TuyaConnectionEstablished,
    TuyaResponseReceived,
    TuyaStateUpdated,
)
from local_tuya.tuya.message import StateCommand, StateResponse, StatusResponse
from local_tuya.tuya.state import State


@pytest.fixture
def state(notifier):
    return State("test", 0.01, notifier)


async def test_connection_lifecycle(
    state, notifier, notifier_spy, assert_event_emitted
):
    with state:
        await asyncio.sleep(0.015)
        notifier_spy.assert_not_called()
        await notifier.emit(TuyaConnectionEstablished())
        await asyncio.sleep(0.005)
        assert_event_emitted(TuyaCommandSent(StateCommand()), 1)
        await notifier.emit(TuyaConnectionClosed(None))
        notifier_spy.reset_mock()
        await asyncio.sleep(0.015)
        notifier_spy.assert_not_called()


@pytest.mark.usefixtures("state")
async def test_updates(notifier, notifier_spy, assert_event_emitted):
    await notifier.emit(TuyaResponseReceived(0, StateResponse({"1": 1, "2": 1}), None))
    # Wrong to_xml_dict, should not fail.
    assert_event_emitted(TuyaStateUpdated({"1": 1, "2": 1}), 0)
    await notifier.emit(
        TuyaResponseReceived(0, StateResponse({"dps": {"1": 1, "2": 1}}), None)
    )
    assert_event_emitted(TuyaStateUpdated({"1": 1, "2": 1}), 1)
    await notifier.emit(
        TuyaResponseReceived(0, StatusResponse({"dps": {"2": 2}}), None)
    )
    assert_event_emitted(TuyaStateUpdated({"1": 1, "2": 2}), 1)
