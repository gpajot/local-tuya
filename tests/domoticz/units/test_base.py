import sys

import pytest

from local_tuya.domoticz.units.base import Unit, UnitAdjustment, UnitCommand, UnitValues


@pytest.fixture()
def domoticz_unit(mocker):
    mock = mocker.Mock()
    mock.Adjustment = 0
    mock.Multiplier = 0
    return mock


@pytest.fixture()
def domoticz_unit_init(mocker, domoticz_unit):
    return mocker.patch(
        "local_tuya.domoticz.units.base.DomoticzEx.Unit", return_value=domoticz_unit
    )


@pytest.fixture()
def command_func(mocker):
    if sys.version_info < (3, 8):
        return None
    return mocker.AsyncMock()


@pytest.fixture()
def unit(domoticz_unit_init, command_func):
    return Unit(
        id_=1,
        type_="the-type",
        name="the-unit",
        image=2,
        to_unit_values=lambda v, f: UnitValues(int(v), str(f(float(v)))),
        command_to_value=lambda cmd, f: f"{cmd.command}-{f(cmd.level)}",
        command_func=command_func,
        options={"k": "v"},
    )


def test_unit_creation(unit, domoticz_unit_init):
    unit.ensure(None, "the-device")
    domoticz_unit_init.assert_called_once_with(
        Name="the-device the-unit",
        DeviceID="the-device",
        Unit=1,
        Image=2,
        TypeName="the-type",
        Options={"k": "v"},
    )


def test_unit_update(unit, domoticz_unit):
    unit.ensure(domoticz_unit, "the-device")
    assert domoticz_unit.Image == 2
    domoticz_unit.Update.assert_called_once_with(False)


async def test_on_command_not_ensured(unit):
    with pytest.raises(RuntimeError):
        await unit.on_command(UnitCommand("cmd", 1.1, ""))


async def test_on_command(unit, command_func, domoticz_unit):
    domoticz_unit.Adjustment = -0.1
    unit.ensure(None, "the-device")
    await unit.on_command(UnitCommand("cmd", 1, ""))

    if command_func:
        command_func.assert_awaited_once_with("cmd-1.1")


def test_update(unit, domoticz_unit):
    domoticz_unit.Adjustment = -0.1
    unit.ensure(None, "the-device")

    unit.update("1")

    assert unit._unit.nValue == 1
    assert unit._unit.sValue == "0.9"
    unit._unit.Update.assert_called_once()


def test_update_not_ensured(unit):
    with pytest.raises(RuntimeError):
        unit.update("1")


@pytest.mark.parametrize(
    ("adjustment", "multiplier", "expected"),
    [
        (None, None, 10),
        (0, 0, 10),
        (-1, 0, 9),
        (0, 2, 20),
        (-1, 2, 18),
    ],
)
def test_unit_adjustment(adjustment, multiplier, expected, domoticz_unit):
    domoticz_unit.Adjustment = adjustment
    domoticz_unit.Multiplier = multiplier
    unit_adjust = UnitAdjustment(domoticz_unit)

    adjusted = unit_adjust.adjust_value(10)
    assert adjusted == expected
    assert unit_adjust.adjust_command(adjusted) == 10
