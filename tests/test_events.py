import sys
import types

import pytest

from local_tuya.events import Event, EventNotifier


class Event1(Event):
    ...


class Event2(Event):
    ...


@pytest.mark.skipif(
    sys.version_info < (3, 8),
    reason="requires python3.8 or higher for AsyncMock",
)
async def test_event_notifier(mocker):
    listener1 = mocker.Mock()
    listener2 = mocker.Mock()
    listener2_async = mocker.AsyncMock(spec=types.FunctionType)
    notifier = EventNotifier()
    notifier.register(Event1, listener1)
    notifier.register(Event2, listener2)
    notifier.register(Event2, listener2_async)

    event1 = Event1()
    await notifier.emit(event1)
    listener1.assert_called_with(event1)
    listener2.assert_not_called()
    listener2_async.assert_not_called()
    listener1.reset_mock()

    event2 = Event2()
    await notifier.emit(event2)
    listener1.assert_not_called()
    listener2.assert_called_with(event2)
    listener2_async.assert_awaited_with(event2)
