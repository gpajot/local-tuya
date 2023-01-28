import asyncio

import pytest

from local_tuya.device.state import StateHandler


@pytest.fixture()
def callback(mocker):
    fut: asyncio.Future[None] = asyncio.Future()
    fut.set_result(None)
    return mocker.Mock(return_value=fut)


@pytest.fixture()
def handler(callback):
    return StateHandler(callback)


async def test_state_updated(handler, callback):
    await handler.updated({"1": 1})

    assert await handler.state() == {"1": 1}
    callback.assert_called_once_with({"1": 1})


async def test_matches(handler):
    task = asyncio.create_task(handler.matches({"1": 1, "2": 2}))
    await asyncio.sleep(0)  # context switch
    assert not task.done()
    await handler.updated({"1": 1})
    await asyncio.sleep(0)  # context switch
    assert not task.done()
    await handler.updated({"1": 1, "2": 2})
    await asyncio.wait_for(task, 0.001)
    await task
