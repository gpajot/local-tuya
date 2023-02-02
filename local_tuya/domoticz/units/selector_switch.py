from enum import Enum
from typing import Awaitable, Callable, Dict, List, Optional, Type, TypeVar

from local_tuya.domoticz.units.base import Unit, UnitCommand, UnitValues

T = TypeVar("T", bound=Enum)


class SelectorSwitchStyle(str, Enum):
    BUTTON_BAR = "0"
    DROP_DOWN = "1"


def selector_switch_unit(
    id_: int,
    name: str,
    image: int,
    # All possible values.
    # Names will be used for labels.
    # Values should correspond to what is sent to the tuya device.
    enum: Type[T],
    command_func: Callable[[T], Awaitable],
    off_label: str = "Off",
    off_hidden: bool = True,
    style: SelectorSwitchStyle = SelectorSwitchStyle.BUTTON_BAR,
) -> Unit[T]:
    _value_to_level: Dict[T, int] = {}
    _level_to_value: Dict[int, T] = {}
    labels: List[str] = [off_label]
    e: T
    for i, e in enumerate(enum, start=1):
        _value_to_level[e] = i * 10
        _level_to_value[i * 10] = e
        labels.append(f"{e.name[0]}{e.name[1:].lower()}")  # type: ignore

    def _to_unit_values(value: T) -> UnitValues:
        level = _value_to_level.get(value, 0)
        return UnitValues(
            n_value=1 if level else 0,
            s_value=str(level),
        )

    def _command_to_value(command: UnitCommand) -> Optional[T]:
        return _level_to_value.get(int(command.level))

    return Unit(
        id_=id_,
        type_="Selector Switch",
        name=name,
        image=image,
        to_unit_values=_to_unit_values,
        command_to_value=_command_to_value,
        command_func=command_func,
        options={
            "LevelActions": "|".join(["" for _ in labels]),
            "LevelNames": "|".join(labels),
            "LevelOffHidden": str(off_hidden).lower(),
            "SelectorStyle": style.value,
        },
    )
