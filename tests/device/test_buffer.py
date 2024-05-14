import asyncio

import pytest

from local_tuya.device.buffer import UpdateBuffer
from local_tuya.device.state import StateHandler
from local_tuya.protocol import Protocol


class TestUpdateBuffer:
    @pytest.fixture()
    def protocol(self, mocker):
        return mocker.MagicMock(spec=Protocol)

    @pytest.fixture()
    def state_handler(self, mocker):
        return mocker.MagicMock(spec=StateHandler)

    @pytest.fixture()
    def buffer(self, protocol, state_handler):
        return UpdateBuffer(0.01, 0.01, protocol, state_handler, None)

    async def test__filter(self, buffer, state_handler):
        state_handler.get.return_value = {"1": 1, "2": 2}

        filtered = await buffer._filter({"1": 2, "2": 2})

        assert filtered == {"1": 2}

    async def test_buffer_updates(self, buffer, protocol, state_handler):
        state_handler.get.return_value = {"1": 1, "2": 2}

        with buffer:
            update1 = asyncio.create_task(buffer.update({"1": 2}))
            await asyncio.sleep(0.001)  # context switch
            update2 = asyncio.create_task(buffer.update({"2": 3}))
            await update1
            await update2

        protocol.update.assert_awaited_once_with({"1": 2, "2": 3})

    async def test_buffer_updates_rollback(self, buffer, protocol, state_handler):
        state_handler.get.return_value = {"1": 1, "2": 2}

        with buffer:
            update1 = asyncio.create_task(buffer.update({"1": 2}))
            await asyncio.sleep(0.001)  # context switch
            update2 = asyncio.create_task(buffer.update({"1": 1}))
            await update1
            await update2

        protocol.update.assert_not_called()

    async def test_no_buffer_updates(self, buffer, protocol, state_handler):
        state_handler.get.return_value = {"1": 1, "2": 2}

        with buffer:
            update1 = asyncio.create_task(buffer.update({"1": 2}))
            await asyncio.sleep(0.015)  # > delay
            update2 = asyncio.create_task(buffer.update({"2": 3}))
            await update1
            await update2

        assert protocol.update.call_count == 2
        protocol.update.assert_has_calls(
            (
                (({"1": 2},), {}),
                (({"2": 3},), {}),
            )
        )

    async def test_buffer_no_update(self, buffer, protocol, state_handler):
        state_handler.get.return_value = {"1": 1, "2": 2}

        with buffer:
            await buffer.update({"1": 1})

        protocol.update.assert_not_called()

    async def test_confirm_timeout(self, buffer, protocol, state_handler):
        state_handler.get.return_value = {"1": 1, "2": 2}

        async def _sleep(_):
            await asyncio.sleep(0.1)  # > timeout

        state_handler.matches = _sleep

        with buffer:
            with pytest.raises(asyncio.TimeoutError):
                await buffer.update({"1": 2})
