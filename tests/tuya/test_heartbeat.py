import asyncio

import pytest

from local_tuya.tuya.events import (
    TuyaCommandSent,
    TuyaConnectionClosed,
    TuyaConnectionEstablished,
)
from local_tuya.tuya.heartbeat import Heartbeat
from local_tuya.tuya.message import HeartbeatCommand


@pytest.fixture
def heartbeat(notifier):
    return Heartbeat("test", 0.01, notifier)


async def test_heartbeat(heartbeat, notifier, notifier_spy, assert_event_emitted):
    with heartbeat:
        await asyncio.sleep(0.015)
        notifier_spy.assert_not_called()
        await notifier.emit(TuyaConnectionEstablished())
        await asyncio.sleep(0.015)
        assert_event_emitted(TuyaCommandSent(HeartbeatCommand()), 2)
        await notifier.emit(TuyaConnectionClosed(None))
        notifier_spy.reset_mock()
        await asyncio.sleep(0.015)
        notifier_spy.assert_not_called()
