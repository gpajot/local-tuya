from typing import Awaitable, Callable

from local_tuya.domoticz.units.base import Unit, UnitCommand, UnitValues


def set_point_unit(
    id_: int,
    name: str,
    image: int,
    command_func: Callable[[float], Awaitable],
) -> Unit[float]:
    def _to_unit_values(value: float) -> UnitValues:
        return UnitValues(n_value=1, s_value=str(round(value, 2)))

    def _command_to_value(command: UnitCommand) -> float:
        return command.level

    return Unit(
        id_=id_,
        type_="Set Point",
        name=name,
        image=image,
        to_unit_values=_to_unit_values,
        command_to_value=_command_to_value,
        command_func=command_func,
    )
