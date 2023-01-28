import json
import logging
from dataclasses import asdict, dataclass
from enum import IntEnum
from typing import Awaitable, Callable, Dict, Generic, Optional, TypeVar

try:
    import DomoticzEx
except ModuleNotFoundError:
    from local_tuya.domoticz.types import DomoticzEx

from local_tuya.domoticz.types import DomoticzUnit

logger = logging.getLogger(__name__)


class ColorMode(IntEnum):
    WHITE = 1
    TEMP = 2
    RGB = 3
    CUSTOM = 4


@dataclass
class Color:
    m: int
    t: int
    r: int
    g: int
    b: int
    cw: int
    ww: int


@dataclass
class UnitCommand:
    command: str
    level: float
    color_str: str

    def color(self) -> Optional[Color]:
        if self.command != "Set Color" or not self.color_str:
            return None
        return Color(**json.loads(self.color_str))


@dataclass
class UnitValues:
    n_value: int
    s_value: str
    color: Optional[Color] = None

    def color_str(self) -> str:
        if not self.color:
            return ""
        return json.dumps(asdict(self.color))


T = TypeVar("T")


class Unit(Generic[T]):
    def __init__(
        self,
        id_: int,
        type_: str,
        name: str,
        image: int,
        to_unit_values: Callable[[T], UnitValues],
        command_to_value: Optional[Callable[[UnitCommand], Optional[T]]] = None,
        command_func: Optional[Callable[[T], Awaitable]] = None,
        options: Optional[Dict[str, str]] = None,
    ):
        self.id = id_
        self._type = type_
        self._name = name
        self._image = image
        self._options = options
        self._unit: Optional[DomoticzUnit] = None
        self._to_unit_values = to_unit_values
        self._command_to_value = command_to_value
        self._command_func = command_func

    def ensure(self, unit: Optional[DomoticzUnit], device_name: str) -> None:
        if unit is None:
            logger.info("creating unit %s for device %s", self._name, device_name)
            full_name = f"{device_name} {self._name}"
            unit = DomoticzEx.Unit(
                Name=full_name,
                DeviceID=device_name,
                Unit=self.id,
                Image=self._image,
                TypeName=self._type,
                **({"Options": self._options} if self._options else {}),
            )
            unit.Create()
        self._unit = unit

    async def on_command(self, command: UnitCommand) -> None:
        if self._command_to_value and self._command_func:
            value = self._command_to_value(command)
            if value is not None:
                await self._command_func(value)

    def update(self, value: T) -> None:
        if self._unit is None:
            raise RuntimeError(f"unit {self.id} {self._name} not registered")
        values = self._to_unit_values(value)
        update = False
        if values.n_value != self._unit.nValue:
            self._unit.nValue = values.n_value
            update = True
        if values.s_value != self._unit.sValue:
            self._unit.sValue = values.s_value
            update = True
        color = values.color_str()
        if color and color != self._unit.Color:
            self._unit.Color = color
            update = True
        if update:
            self._unit.Update(Log=True)
