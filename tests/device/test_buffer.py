import asyncio
from unittest.mock import call

import pytest

from local_tuya.backoff import SequenceBackoff
from local_tuya.device.buffer import UpdateBuffer
from local_tuya.tuya import TuyaProtocol, TuyaStateUpdated


@pytest.fixture
def protocol(mocker):
    return mocker.MagicMock(spec=TuyaProtocol)


@pytest.fixture
async def buffer(protocol, notifier):
    buf = UpdateBuffer(
        device_name="test",
        delay=0.01,
        protocol=protocol,
        event_notifier=notifier,
        constraints=None,
        retries=2,
        retry_backoff=SequenceBackoff(0.01),
    )
    await notifier.emit(TuyaStateUpdated({"1": 1, "2": 2}))
    try:
        yield buf
    finally:
        buf.close()


async def test_filter_with_state(buffer):
    filtered = await buffer._filter({"1": 2, "2": 2})
    assert filtered == {"1": 2}


async def test_no_update(buffer, protocol):
    await buffer.update({"1": 1})

    protocol.update.assert_not_called()


async def test_updates_buffered(buffer, protocol):
    update1 = asyncio.create_task(buffer.update({"1": 2}))
    await asyncio.sleep(0)  # context switch
    update2 = asyncio.create_task(buffer.update({"2": 3}))
    await update1
    await update2

    protocol.update.assert_awaited_once_with({"1": 2, "2": 3})


async def test_buffered_update_rollback(buffer, protocol):
    update1 = asyncio.create_task(buffer.update({"1": 2}))
    await asyncio.sleep(0)  # context switch
    update2 = asyncio.create_task(buffer.update({"1": 1}))
    await update1
    await update2

    protocol.update.assert_not_called()


async def test_updates_not_buffered(buffer, protocol, notifier):
    update1 = asyncio.create_task(buffer.update({"1": 2}))
    await asyncio.sleep(0.015)  # > delay
    await notifier.emit(TuyaStateUpdated({"1": 2, "2": 2}))
    update2 = asyncio.create_task(buffer.update({"2": 3}))
    await update1
    await update2

    assert protocol.update.call_args_list == [
        call({"1": 2}),
        call({"2": 3}),
    ]


async def test_updates_not_buffered_and_state_not_updated(buffer, protocol, notifier):
    update1 = asyncio.create_task(buffer.update({"1": 2}))
    await asyncio.sleep(0.015)  # > delay
    update2 = asyncio.create_task(buffer.update({"2": 3}))
    await update1
    await update2

    assert protocol.update.call_args_list == [
        call({"1": 2}),
        # Since the state is not updated, the previous update is still prending.
        call({"1": 2, "2": 3}),
    ]


async def test_retry_ok(buffer, protocol, notifier):
    await buffer.update({"1": 2})
    await asyncio.sleep(0.015)  # Wait for the first retry to proceed.
    await notifier.emit(TuyaStateUpdated({"1": 2, "2": 2}))
    await buffer._retry_task

    # Should have tried once, and retried once.
    assert protocol.update.call_args_list == [
        call({"1": 2}),
        call({"1": 2}),
    ]


async def test_retry_ko(buffer, protocol, notifier):
    await buffer.update({"1": 2})
    await buffer._retry_task

    # Should have tried once, and retried 2 times.
    assert protocol.update.call_args_list == [
        call({"1": 2}),
        call({"1": 2}),
        call({"1": 2}),
    ]
