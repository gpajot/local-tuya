import logging
from typing import Callable, Dict, Generic, Optional, TypeVar

from concurrent_tasks import BlockingThreadedTaskPool

from local_tuya.device import Device, State
from local_tuya.domoticz.logger import DomoticzHandler
from local_tuya.domoticz.types import DomoticzDevice
from local_tuya.domoticz.units import UnitCommand, UnitManager
from local_tuya.protocol import ProtocolConfig

logger = logging.getLogger(__name__)
LOG_HANDLER = DomoticzHandler()

T = TypeVar("T", bound=State)
OnStart = Callable[[ProtocolConfig, Dict[str, str], UnitManager[T]], Device[T]]


class Plugin(Generic[T]):
    """Defines the Domoticz plugin.
    It connects the device to Domoticz units.
    """

    def __init__(self, package: str, on_start: OnStart):
        self._on_start = on_start
        self._manager: Optional[UnitManager[T]] = None
        self._task_pool: Optional[BlockingThreadedTaskPool] = None
        # Setup loggers to log in Domoticz.
        for pkg in ("local_tuya", package):
            _logger = logging.getLogger(pkg)
            _logger.addHandler(LOG_HANDLER)
            _logger.setLevel(logging.DEBUG)

    @staticmethod
    def _protocol_config(parameters: Dict[str, str]) -> ProtocolConfig:
        return ProtocolConfig(
            id_=parameters["Username"],
            address=parameters["Address"],
            port=int(parameters["Port"]),
            key=parameters["Password"].encode(),
        )

    def start(
        self,
        parameters: Dict[str, str],
        devices: Dict[str, DomoticzDevice],
    ) -> None:
        """Start the device in a separate thread."""
        self.stop()
        name = parameters["Name"]
        self._manager = UnitManager(
            name=name,
            units=devices[name].Units if name in devices else {},
        )
        device = self._on_start(
            self._protocol_config(parameters), parameters, self._manager
        )
        device.set_state_updated_callback(self._manager.update)
        self._task_pool = BlockingThreadedTaskPool(context_manager=device)
        self._task_pool.start()

    def stop(self) -> None:
        """Stop the device if started."""
        if self._task_pool:
            self._task_pool.stop()
            self._task_pool = None
        self._manager = None

    def on_command(self, unit_id: int, command: UnitCommand) -> None:
        """Send an command to the device asynchronously."""
        if self._task_pool and self._manager:
            # Fire and forget.
            self._task_pool.create_task(
                self._on_command(self._manager, unit_id, command)
            )
        else:
            logger.warning(
                "error sending command %s to unit %d, plugin %s not started",
                command,
                unit_id,
                self.__class__.__qualname__,
            )

    async def _on_command(
        self,
        manager: UnitManager[T],
        unit_id: int,
        command: UnitCommand,
    ) -> None:
        """Suppresses and logs exceptions."""
        try:
            await manager.on_command(unit_id, command)
        except Exception:
            logger.exception(
                "error sending command %s to unit %s of plugin %s",
                command,
                unit_id,
                self.__class__.__qualname__,
            )
