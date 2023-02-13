import pytest

from local_tuya.domoticz.units.base import UnitValues
from local_tuya.domoticz.units.temperature import temperature_unit


@pytest.fixture()
def unit_kwargs(mocker):
    unit = mocker.patch("local_tuya.domoticz.units.temperature.Unit")
    temperature_unit(1, "", 1)
    unit.assert_called_once()
    return unit.call_args[1]


def test_to_unit_values(unit_kwargs):
    to_unit_values = unit_kwargs["to_unit_values"]
    assert to_unit_values(10.2, lambda f: f) == UnitValues(1, "10.2")
    assert to_unit_values(10.2, lambda f: f - 0.1) == UnitValues(1, "10.1")
