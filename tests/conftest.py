import contextlib
from dataclasses import fields, is_dataclass

import pytest

from local_tuya.events import EventNotifier
from local_tuya.protocol.events import ConnectionEstablished
from local_tuya.protocol.message import HeartbeatCommand, StateCommand, StatusResponse


@pytest.fixture
def notifier():
    return EventNotifier()


@pytest.fixture
def notifier_spy(mocker, notifier):
    return mocker.spy(notifier, "emit")


@pytest.fixture
def assert_event_emitted(notifier_spy):
    def _assert_equal(a, b):
        assert type(a) is type(b)
        if isinstance(a, (ConnectionEstablished, HeartbeatCommand, StateCommand)):
            return
        if isinstance(a, StatusResponse):
            assert a.error == b.error
            assert a.values == b.values
        if is_dataclass(a) and is_dataclass(type(a)):
            for field in fields(a):
                _assert_equal(getattr(a, field.name), getattr(b, field.name))
            return
        assert a == b

    def _assert(expected_event, count):
        n = 0
        for call in notifier_spy.call_args_list:
            if len(call[0]) == 1 and type(expected_event) is type(  # noqa: E721
                call[0][0]
            ):
                actual_event = call[0][0]
                with contextlib.suppress(Exception):
                    _assert_equal(expected_event, actual_event)
                    n += 1
        assert n == count, f"incorrect number of event {expected_event} emitted"

    return _assert
