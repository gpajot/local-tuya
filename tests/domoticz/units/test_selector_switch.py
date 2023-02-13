import asyncio
from enum import Enum

import pytest

from local_tuya.domoticz.units.base import UnitCommand, UnitValues
from local_tuya.domoticz.units.selector_switch import selector_switch_unit


class TheEnum(str, Enum):
    ONE = "one"
    TWO = "two"


@pytest.fixture()
def unit_kwargs(mocker):
    unit = mocker.patch("local_tuya.domoticz.units.selector_switch.Unit")
    selector_switch_unit(1, "", 1, TheEnum, lambda _: asyncio.Future())
    unit.assert_called_once()
    return unit.call_args[1]


def test_to_unit_values(unit_kwargs):
    to_unit_values = unit_kwargs["to_unit_values"]

    assert to_unit_values(TheEnum.ONE, None) == UnitValues(1, "10")
    assert to_unit_values(TheEnum.TWO, None) == UnitValues(1, "20")
    assert to_unit_values("something else", None) == UnitValues(0, "0")


def test_command_to_value(unit_kwargs):
    command_to_value = unit_kwargs["command_to_value"]

    assert command_to_value(UnitCommand("", 10, ""), None) is TheEnum.ONE
    assert command_to_value(UnitCommand("", 20, ""), None) is TheEnum.TWO
    assert command_to_value(UnitCommand("", 0, ""), None) is None


def test_options(unit_kwargs):
    assert unit_kwargs["options"] == {
        "LevelActions": "||",
        "LevelNames": "Off|One|Two",
        "LevelOffHidden": "true",
        "SelectorStyle": "0",
    }
