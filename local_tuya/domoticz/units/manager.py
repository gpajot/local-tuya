import logging
from typing import Any, Callable, Dict, Generic, TypeVar

from local_tuya.device import State
from local_tuya.domoticz.types import DomoticzUnit
from local_tuya.domoticz.units.base import Unit, UnitCommand

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=State)
V = TypeVar("V")


class UnitManager(Generic[T]):
    def __init__(self, name: str, units: Dict[int, DomoticzUnit]):
        super().__init__()
        self._name = name
        self._domoticz_units = units
        self._units: Dict[int, Unit] = {}
        self._value_from_state: Dict[int, Callable[[T], Any]] = {}

    def register(self, unit: Unit[V], value_from_state: Callable[[T], V]) -> None:
        self._units[unit.id] = unit
        self._value_from_state[unit.id] = value_from_state
        unit.ensure(self._domoticz_units.get(unit.id), self._name)

    def remove(self, unit_id: int) -> None:
        if unit_id in self._domoticz_units:
            self._domoticz_units[unit_id].Delete()

    async def on_command(self, unit_id: int, command: UnitCommand) -> None:
        unit = self._units.get(unit_id)
        if unit:
            logger.debug("sending command %s to unit %s", command, unit_id)
            await unit.on_command(command)

    def update(self, state: T) -> None:
        logger.debug("received new device state: %s", state)
        for id_, unit in self._units.items():
            unit.update(self._value_from_state[id_](state))
