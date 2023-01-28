import sys

import pytest

from local_tuya.device import State
from local_tuya.domoticz.types import DomoticzUnit
from local_tuya.domoticz.units.base import Unit, UnitCommand
from local_tuya.domoticz.units.manager import UnitManager


@pytest.fixture()
def unit(mocker):
    unit = mocker.Mock(spec=Unit)
    unit.id = 1
    return unit


@pytest.fixture()
def domoticz_unit(mocker):
    return mocker.Mock(spec=DomoticzUnit)


@pytest.fixture()
def value_from_state(mocker):
    return mocker.Mock()


@pytest.fixture()
def manager(unit, value_from_state, domoticz_unit):
    manager: UnitManager = UnitManager("the-device", {1: domoticz_unit})
    manager.register(unit, value_from_state)
    return manager


@pytest.fixture()
def state(mocker):
    return mocker.Mock(spec=State)


@pytest.mark.usefixtures("manager")
def test_register(unit, domoticz_unit):
    unit.ensure.assert_called_once_with(domoticz_unit, "the-device")


@pytest.mark.skipif(
    sys.version_info < (3, 8),
    reason="requires python3.8 or higher for AsyncMock",
)
async def test_on_command(manager, unit):
    await manager.on_command(1, UnitCommand("cmd", 10.2, ""))

    unit.on_command.assert_awaited_once_with(UnitCommand("cmd", 10.2, ""))


async def test_on_command_no_unit(manager, unit):
    # Should not fail.
    await manager.on_command(2, UnitCommand("cmd", 10.2, ""))

    unit.on_command.assert_not_called()


def test_update(manager, unit, state, value_from_state):
    value_from_state.side_effect = lambda s: id(s)

    manager.update(state)

    unit.update.assert_called_once_with(id(state))
