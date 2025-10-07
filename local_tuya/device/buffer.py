import asyncio
import logging

from concurrent_tasks import BackgroundTask

from local_tuya.backoff import SequenceBackoff
from local_tuya.device.constraints import Constraints
from local_tuya.events import EventNotifier
from local_tuya.protocol import Values
from local_tuya.tuya import TuyaProtocol, TuyaStateUpdated

logger = logging.getLogger(__name__)


class UpdateBuffer:
    """Debounce updates to the device."""

    def __init__(
        self,
        device_name: str,
        delay: float,
        protocol: TuyaProtocol,
        event_notifier: EventNotifier,
        constraints: Constraints | None,
        retries: int,
        retry_backoff: SequenceBackoff,
    ):
        event_notifier.register(TuyaStateUpdated, self._set_state)
        self._name = device_name
        self._protocol = protocol

        self._state: Values | None = None
        self._state_updated = asyncio.Event()
        self._buffer: Values = {}
        self._constraints = constraints

        self._delay = delay
        # Allow a single call to the device, and lock management of update task.
        self._update_finished = asyncio.Event()
        self._update_finished.set()
        self._update_waiter: asyncio.Future[None] | None = None
        self._update_task = BackgroundTask(self._update)

        self._retries = retries
        self._retry_backoff = retry_backoff
        self._retry_task: BackgroundTask | None = None

    def close(self) -> None:
        self._update_task.cancel()
        if self._retry_task:
            self._retry_task.cancel()

    def _set_state(self, event: TuyaStateUpdated) -> None:
        self._state = event.values
        self._state_updated.set()

    async def update(self, values: Values) -> None:
        # Store the values first in case we time out.
        if values:
            self._buffer = await self._filter(values)
        # Make sure nothing is currently updating the device.
        await self._update_finished.wait()
        # Stop any update currently in the buffer stage.
        self._update_task.cancel()
        if self._buffer:
            self._update_task.create()
            if not self._update_waiter:
                self._update_waiter = asyncio.Future()
            await self._update_waiter
        else:
            logger.debug(
                "%s: cancelling previous commands as update is no longer required",
                self._name,
            )
            if self._update_waiter:
                self._update_waiter.set_result(None)
                self._update_waiter = None

    async def _update(self) -> None:
        if self._delay:
            logger.debug(
                "%s: received command waiting %ss before sending to device",
                self._name,
                self._delay,
            )
            await asyncio.sleep(self._delay)
        if not self._buffer:
            return
        logger.debug("%s: updating device with: %s", self._name, self._buffer)
        self._update_finished.clear()
        try:
            await self._protocol.update(self._buffer.copy())
            if self._update_waiter:
                self._update_waiter.set_result(None)
            # This should not go in the `finally` as we don't want to retry if cancelled.
            self._start_check_and_retry()
        except Exception as e:
            if self._update_waiter:
                self._update_waiter.set_exception(e)
            self._start_check_and_retry()
        finally:
            self._update_finished.set()
            self._update_waiter = None

    async def _filter(self, values: Values) -> Values:
        """Filter the new values to take into account:
        - values already equal to the value from the current device state
        - constraints.
        """
        if self._state is None:
            await self._state_updated.wait()
        assert self._state is not None
        filtered = {
            k: v for k, v in {**self._buffer, **values}.items() if self._state[k] != v
        }
        if not self._constraints:
            return filtered
        return self._constraints.filter_values(filtered, self._state)

    def _start_check_and_retry(self) -> None:
        if not self._retries or self._retry_task:
            return
        self._retry_task = BackgroundTask(self._check_and_retry)
        task = self._retry_task.create()

        def _cleanup(_: asyncio.Task) -> None:
            self._retry_task = None

        task.add_done_callback(_cleanup)

    async def _check_and_retry(self) -> None:
        """Retry unless the state received from the device matches the update."""
        assert self._state is not None
        with self._retry_backoff:
            i = 0
            while True:
                await self._retry_backoff.wait()
                # Filter the buffer with the current state.
                self._buffer = {
                    k: v for k, v in self._buffer.items() if self._state[k] != v
                }
                if not self._buffer:
                    if i == 0:
                        logger.debug("%s: update confirmed", self._name)
                    else:
                        logger.debug(
                            "%s: update confirmed after retry %i", self._name, i
                        )
                    return
                if i == self._retries:
                    logger.error(
                        "%s: update still not confirmed after %i retries, aborting",
                        self._name,
                        i,
                    )
                    return
                logger.debug(
                    "%s: update not confirmed, attempting new update, retry %i...",
                    self._name,
                    i + 1,
                )
                # Retry to send what is left in the buffer.
                try:
                    await self.update({})
                except Exception:
                    logger.error(
                        "%s: exception caught retrying update",
                        self._name,
                        exc_info=True,
                    )
                i += 1
