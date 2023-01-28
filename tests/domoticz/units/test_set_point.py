import asyncio

import pytest

from local_tuya.domoticz.units.base import UnitCommand, UnitValues
from local_tuya.domoticz.units.set_point import set_point_unit


@pytest.fixture()
def unit_kwargs(mocker):
    unit = mocker.patch("local_tuya.domoticz.units.set_point.Unit")
    set_point_unit(1, "", 1, lambda _: asyncio.Future())
    unit.assert_called_once()
    return unit.call_args[1]


def test_to_unit_values(unit_kwargs):
    to_unit_values = unit_kwargs["to_unit_values"]
    assert to_unit_values(10.2) == UnitValues(1, "10.2")


def test_command_to_value(unit_kwargs):
    command_to_value = unit_kwargs["command_to_value"]
    assert command_to_value(UnitCommand("", 10.2, "")) == 10.2
