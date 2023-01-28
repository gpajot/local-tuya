from typing import Awaitable, Callable

from local_tuya.domoticz.units.base import Unit, UnitCommand, UnitValues


def switch_unit(
    id_: int,
    name: str,
    image: int,
    command_func: Callable[[bool], Awaitable],
) -> Unit[bool]:
    def _to_unit_values(value: bool) -> UnitValues:
        if value:
            return UnitValues(n_value=1, s_value="On")
        return UnitValues(n_value=0, s_value="Off")

    def _command_to_value(command: UnitCommand) -> bool:
        return command.command.lower() == "on"

    return Unit(
        id_=id_,
        type_="Switch",
        name=name,
        image=image,
        to_unit_values=_to_unit_values,
        command_to_value=_command_to_value,
        command_func=command_func,
    )
