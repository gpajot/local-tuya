import inspect
from collections import defaultdict
from typing import Any, Awaitable, Callable, DefaultDict, cast


class Event:
    """Base event class"""


class EventNotifier:
    def __init__(self):
        self._listeners: DefaultDict[
            type[Event], list[Callable[[Event], Awaitable[None]]]
        ] = defaultdict(list)

    def register[T: Event](
        self, event_class: type[T], listener: Callable[[T], Any]
    ) -> None:
        self._listeners[event_class].append(
            cast(
                Callable[[Event], Awaitable[None]],
                _make_async(listener),
            )
        )

    async def emit(self, event: Event) -> None:
        for listener in self._listeners[type(event)]:
            await listener(event)


def _make_async[**P](func: Callable[P, Any]) -> Callable[P, Awaitable[None]]:
    async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        res = func(*args, **kwargs)
        if inspect.iscoroutine(res):
            await res

    return _wrapper
