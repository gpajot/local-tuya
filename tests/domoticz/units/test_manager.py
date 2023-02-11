import sys

import pytest

from local_tuya.device import State
from local_tuya.domoticz.types import DomoticzUnit
from local_tuya.domoticz.units.base import Unit, UnitCommand
from local_tuya.domoticz.units.ids import UnitId
from local_tuya.domoticz.units.manager import UnitManager


class TheUnitId(UnitId):
    ONE = 1
    TWO = 2


@pytest.fixture()
def unit_one(mocker):
    unit = mocker.Mock(spec=Unit)
    unit.id = TheUnitId.ONE
    return unit


@pytest.fixture()
def unit_two(mocker):
    unit = mocker.Mock(spec=Unit)
    unit.id = TheUnitId.TWO
    return unit


@pytest.fixture()
def domoticz_unit_one(mocker):
    return mocker.Mock(spec=DomoticzUnit)


@pytest.fixture()
def domoticz_unit_two(mocker):
    return mocker.Mock(spec=DomoticzUnit)


@pytest.fixture()
def value_from_state(mocker):
    return mocker.Mock()


@pytest.fixture()
def manager(unit_one, value_from_state, domoticz_unit_one, domoticz_unit_two):
    manager: UnitManager = UnitManager(
        "the-device",
        {
            TheUnitId.ONE: domoticz_unit_one,
            TheUnitId.TWO: domoticz_unit_two,
        },
        {TheUnitId.ONE},
    )
    manager.register(unit_one, value_from_state)
    return manager


@pytest.fixture()
def state(mocker):
    return mocker.Mock(spec=State)


@pytest.mark.usefixtures("manager")
def test_register(unit_one, domoticz_unit_one):
    unit_one.ensure.assert_called_once_with(domoticz_unit_one, "the-device")


def test_register_not_included(unit_two, domoticz_unit_two, manager):
    manager.register(unit_two, value_from_state)
    domoticz_unit_two.Delete.assert_called_once()


@pytest.mark.skipif(
    sys.version_info < (3, 8),
    reason="requires python3.8 or higher for AsyncMock",
)
async def test_on_command(manager, unit_one):
    await manager.on_command(1, UnitCommand("cmd", 10.2, ""))

    unit_one.on_command.assert_awaited_once_with(UnitCommand("cmd", 10.2, ""))


async def test_on_command_no_unit(manager, unit_one):
    # Should not fail.
    await manager.on_command(2, UnitCommand("cmd", 10.2, ""))

    unit_one.on_command.assert_not_called()


def test_update(manager, unit_one, state, value_from_state):
    value_from_state.side_effect = lambda s: id(s)

    manager.update(state)

    unit_one.update.assert_called_once_with(id(state))
