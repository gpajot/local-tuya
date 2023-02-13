import sys

import pytest

from local_tuya.domoticz.units.base import Unit, UnitCommand, UnitValues


@pytest.fixture()
def domoticz_unit(mocker):
    return mocker.Mock()


@pytest.fixture()
def domoticz_init(mocker, domoticz_unit):
    return mocker.patch(
        "local_tuya.domoticz.units.base.DomoticzEx.Unit",
        return_value=domoticz_unit,
    )


@pytest.fixture()
def command_func(mocker):
    if sys.version_info < (3, 8):
        return None
    return mocker.AsyncMock()


@pytest.fixture()
def unit(domoticz_init, command_func):
    return Unit(
        id_=1,
        type_="the-type",
        name="the-unit",
        image=2,
        to_unit_values=lambda v: UnitValues(int(v), v),
        command_to_value=lambda cmd: f"{cmd.command}-{cmd.level}",
        command_func=command_func,
        options={"k": "v"},
    )


def test_unit_creation(unit, domoticz_init):
    unit.ensure(None, "the-device")
    domoticz_init.assert_called_once_with(
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


async def test_on_command(unit, command_func):
    await unit.on_command(UnitCommand("cmd", 1.1, ""))

    if command_func:
        command_func.assert_awaited_once_with("cmd-1.1")


def test_update(unit, domoticz_unit):
    unit.ensure(None, "the-device")

    unit.update("1")

    assert domoticz_unit.nValue == 1
    assert domoticz_unit.sValue == "1"
    domoticz_unit.Update.assert_called_once()


def test_update_no_ensured(unit):
    with pytest.raises(RuntimeError):
        unit.update("1")
