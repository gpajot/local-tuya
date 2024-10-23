import asyncio

import pytest

from local_tuya.device.state import StateHandler
from local_tuya.tuya import TuyaStateUpdated


@pytest.fixture
async def handler(notifier):
    return StateHandler("test", notifier)


async def test_state_updated(handler, notifier):
    await notifier.emit(TuyaStateUpdated({"1": 1}))
    assert await handler.get() == {"1": 1}


async def test_matches(handler, notifier):
    task = asyncio.create_task(handler.matches({"1": 1, "2": 2}))
    await asyncio.sleep(0)  # context switch
    assert not task.done()
    await notifier.emit(TuyaStateUpdated({"1": 1}))
    await asyncio.sleep(0)  # context switch
    assert not task.done()
    await notifier.emit(TuyaStateUpdated({"1": 1, "2": 2}))
    await asyncio.wait_for(task, 0.001)
    await task
