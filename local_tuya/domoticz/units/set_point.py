from typing import Awaitable, Callable

from local_tuya.domoticz.units.base import AdjustFunc, Unit, UnitCommand, UnitValues


def set_point_unit(
    id_: int,
    name: str,
    image: int,
    command_func: Callable[[float], Awaitable],
) -> Unit[float]:
    def _to_unit_values(value: float, adjust: AdjustFunc) -> UnitValues:
        return UnitValues(n_value=1, s_value=str(round(adjust(value), 2)))

    def _command_to_value(command: UnitCommand, adjust: AdjustFunc) -> float:
        return adjust(command.level)

    return Unit(
        id_=id_,
        type_="Set Point",
        name=name,
        image=image,
        to_unit_values=_to_unit_values,
        command_to_value=_command_to_value,
        command_func=command_func,
    )
