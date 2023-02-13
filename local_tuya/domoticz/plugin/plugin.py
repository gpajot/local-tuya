import logging
from typing import Callable, Dict, Generic, Optional, Type, TypeVar

from concurrent_tasks import BlockingThreadedTaskPool, ThreadedPoolContextManagerWrapper

from local_tuya.device import Device, State
from local_tuya.domoticz.logger import DomoticzHandler
from local_tuya.domoticz.types import DomoticzDevice
from local_tuya.domoticz.units import UnitCommand, UnitId, UnitManager
from local_tuya.protocol import ProtocolConfig, Version

try:
    import DomoticzEx
except ModuleNotFoundError:
    from local_tuya.domoticz.types import DomoticzEx

logger = logging.getLogger(__name__)
LOG_HANDLER = DomoticzHandler()

T = TypeVar("T", bound=State)
OnStart = Callable[[ProtocolConfig, Dict[str, str], UnitManager[T]], Device[T]]


class Plugin(Generic[T]):
    """Defines the Domoticz plugin.
    It connects the device to Domoticz units.
    """

    def __init__(
        self,
        package: str,
        on_start: OnStart,
        unit_ids: Optional[Type[UnitId]],
    ):
        self._package = package
        self._on_start = on_start
        self._unit_ids = unit_ids
        self._manager: Optional[UnitManager[T]] = None
        self._task_pool: Optional[BlockingThreadedTaskPool] = None
        # Setup loggers to log in Domoticz.
        for pkg in ("local_tuya", package):
            _logger = logging.getLogger(pkg)
            _logger.addHandler(LOG_HANDLER)

    @staticmethod
    def _protocol_config(parameters: Dict[str, str]) -> ProtocolConfig:
        return ProtocolConfig(
            id_=parameters["Username"],
            address=parameters["Address"],
            port=int(parameters["Port"]),
            key=parameters["Password"].encode(),
            version=Version(parameters["Mode4"].encode()),
        )

    def _setup_logging(self, debug: bool) -> None:
        DomoticzEx.Debugging(2 + 4 + 8 if debug else 0)
        # Setup loggers to log in Domoticz.
        for pkg in ("local_tuya", self._package):
            _logger = logging.getLogger(pkg)
            _logger.setLevel(logging.DEBUG if debug else logging.INFO)

    def start(
        self,
        parameters: Dict[str, str],
        devices: Dict[str, DomoticzDevice],
    ) -> None:
        """Start the device in a separate thread."""
        self.stop()
        self._setup_logging(parameters.get("Mode6", "") == "1")
        DomoticzEx.Heartbeat(15)
        name = parameters["Name"]
        included_units = parameters.get("Mode5", "")
        manager: UnitManager[T] = UnitManager(
            name=name,
            units=devices[name].Units if name in devices else {},
            included_units=self._unit_ids.included(included_units)
            if self._unit_ids and included_units
            else None,
        )
        self._manager = manager

        def _get_device() -> Device[T]:
            device = self._on_start(
                self._protocol_config(parameters), parameters, manager
            )
            device.set_state_updated_callback(manager.update)
            return device

        self._task_pool = BlockingThreadedTaskPool(
            context_manager=ThreadedPoolContextManagerWrapper(_get_device),
        )
        self._task_pool.start()

    def stop(self) -> None:
        """Stop the device if started."""
        if self._task_pool:
            self._task_pool.stop()
            self._task_pool = None
        if self._manager:
            self._manager.cleanup_domoticz_references()
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
