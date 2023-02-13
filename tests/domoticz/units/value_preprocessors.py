import time

from local_tuya.domoticz.units.value_preprocessors import debounce, moving_average


def test_moving_average():
    wrapped = moving_average(2)

    assert wrapped(1) == 1
    assert wrapped(2) == 1.5
    assert wrapped(3) == 2.5
    assert wrapped(3) == 3


def test_debounce():
    wrapped = debounce(0.01)

    assert wrapped(1) == 1
    assert wrapped(2) == 1
    time.sleep(0.01)
    assert wrapped(3) == 3
