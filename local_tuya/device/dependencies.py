from typing import Iterator, Optional

from imbue import Package, auto_context

from local_tuya.device.buffer import UpdateBuffer
from local_tuya.device.config import DeviceConfig
from local_tuya.device.constraints import Constraints
from local_tuya.device.state import StateHandler
from local_tuya.protocol import Protocol


class DevicePackage(Package):
    EXTRA_DEPENDENCIES = (StateHandler,)

    def __init__(self, config: DeviceConfig, constraints: Optional[Constraints]):
        self._cfg = config
        self._constraints = constraints

    @auto_context(eager=True)
    def buffer(
        self,
        protocol: Protocol,
        state_handler: StateHandler,
    ) -> Iterator[UpdateBuffer]:
        with UpdateBuffer(
            delay=self._cfg.debounce_updates,
            confirm_timeout=self._cfg.confirm_timeout,
            protocol=protocol,
            state_handler=state_handler,
            constraints=self._constraints,
        ) as buffer:
            yield buffer
