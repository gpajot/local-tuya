import asyncio

import pytest

from local_tuya.protocol.events import (
    CommandSent,
    ConnectionClosed,
    ConnectionEstablished,
)
from local_tuya.protocol.heartbeat import Heartbeat
from local_tuya.protocol.message import HeartbeatCommand


@pytest.fixture()
def heartbeat(notifier):
    return Heartbeat(0.01, notifier)


async def test_heartbeat(heartbeat, notifier, notifier_spy, assert_event_emitted):
    with heartbeat:
        await asyncio.sleep(0.015)
        notifier_spy.assert_not_called()
        await notifier.emit(ConnectionEstablished())
        await asyncio.sleep(0.015)
        assert_event_emitted(CommandSent(HeartbeatCommand()), 2)
        await notifier.emit(ConnectionClosed(None))
        notifier_spy.reset_mock()
        await asyncio.sleep(0.015)
        notifier_spy.assert_not_called()
