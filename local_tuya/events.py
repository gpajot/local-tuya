import inspect
from abc import ABC
from collections import defaultdict
from typing import Any, Awaitable, Callable, DefaultDict, List, Type, TypeVar, cast

from typing_extensions import ParamSpec


class Event(ABC):  # noqa: B024
    """Base event class"""


T = TypeVar("T", bound=Event)


class EventNotifier:
    def __init__(self):
        self._listeners: DefaultDict[
            Type[Event], List[Callable[[Event], Awaitable[None]]]
        ] = defaultdict(list)

    def register(self, event_class: Type[T], listener: Callable[[T], Any]) -> None:
        self._listeners[event_class].append(
            cast(
                Callable[[Event], Awaitable[None]],
                maybe_async(listener),
            )
        )

    async def emit(self, event: Event) -> None:
        for listener in self._listeners[type(event)]:
            await listener(event)


P = ParamSpec("P")


def maybe_async(func: Callable[P, Any]) -> Callable[P, Awaitable[None]]:
    async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        res = func(*args, **kwargs)
        if inspect.iscoroutine(res):
            await res

    return _wrapper
