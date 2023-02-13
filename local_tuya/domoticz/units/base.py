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
        # ID of the unit in Domoticz.
        # It has to be unique for the hardware but not across hardware.
        id_: int,
        # Domoticz unit type.
        type_: str,
        # Name that will be suffixed to the hardware name.
        name: str,
        # Image ID, see `/json.htm?type=custom_light_icons` in Domoticz.
        image: int,
        # Convert the value of the unit into the Domoticz unit values.
        to_unit_values: Callable[[T], UnitValues],
        # Convert a Domoticz command into this units value.
        command_to_value: Optional[Callable[[UnitCommand], Optional[T]]] = None,
        # Function to call when a unit command is triggered.
        command_func: Optional[Callable[[T], Awaitable]] = None,
        # Options for unit creation.
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
            logger.info("creating unit %s (%s)", self._name, self.id)
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
        else:
            # Update some unit attributes.
            unit.Image = self._image
            # Should be read/write but raises `AttributeError: readonly attribute`.
            # if self._options:
            #     unit.Options = self._options
            unit.Update(False)
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
