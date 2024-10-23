import time

from local_tuya.device.value_processors import debounce, moving_average


def test_moving_average():
    processor = moving_average(2)

    assert processor(1) == 1
    assert processor(2) == 1.5
    assert processor(3) == 2.5
    assert processor(3) == 3


def test_debounce():
    processor = debounce(0.01)

    assert processor(1) == 1
    assert processor(2) == 1
    time.sleep(0.01)
    assert processor(3) == 3
