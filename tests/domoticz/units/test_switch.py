import asyncio

import pytest

from local_tuya.domoticz.units.base import UnitCommand, UnitValues
from local_tuya.domoticz.units.switch import switch_unit


@pytest.fixture()
def unit_kwargs(mocker):
    unit = mocker.patch("local_tuya.domoticz.units.switch.Unit")
    switch_unit(1, "", 1, lambda _: asyncio.Future())
    unit.assert_called_once()
    return unit.call_args[1]


def test_to_unit_values(unit_kwargs):
    to_unit_values = unit_kwargs["to_unit_values"]

    assert to_unit_values(True) == UnitValues(1, "On")
    assert to_unit_values(False) == UnitValues(0, "Off")


def test_command_to_value(unit_kwargs):
    command_to_value = unit_kwargs["command_to_value"]

    assert command_to_value(UnitCommand("On", 1, "")) is True
    assert command_to_value(UnitCommand("off", 0, "")) is False
