from __future__ import annotations

import inspect
from asyncio import Event
from collections import defaultdict
from contextlib import suppress
from typing import Any, Callable, Generic, Self, TypeVar
from weakref import WeakMethod

ReactrType = TypeVar("ReactrType")


class Reactr(Generic[ReactrType]):
    """A descriptor class."""

    def __init__(self, default: ReactrType) -> None:
        self._default = default

    def __set_name__(self, owner: Any, name: str) -> None:
        self.name = name
        self.private_name = "reactr_" + name

    def __get__(self, obj: ReactrModel, type: type[ReactrModel]) -> ReactrType:
        if obj is None:
            return self.name
        return obj.__dict__.get(self.private_name) or self._default

    def __set__(self, obj: ReactrModel, value: ReactrType) -> None:
        obj.__dict__[self.private_name] = value
        self._trigger(obj, self.name, value)

    def _trigger(self, obj: ReactrModel, name, value):
        for subscr in obj._subscriptions.get(name, []):
            subscr(obj)

        for subscr in obj._weakmethod_subscriptions.get(name, []):
            subscr()(obj)

        if name in obj._watch_events:
            obj._watch_events[name].set()
            obj._watch_events[name].clear()


class ReactrModel:
    def __init__(self) -> None:
        self._subscriptions: dict[str, list[Callable]] = defaultdict(list)
        self._weakmethod_subscriptions: dict[str, list[WeakMethod]] = {}

        self._watch_events: dict[str, Event] = {}

    def subscribe(self, property: str, callback: Callable[[Self], None]) -> None:
        if inspect.ismethod(callback):
            weakref = WeakMethod(callback, self.unsubscribe)

            self._weakmethod_subscriptions.setdefault(property, []).append(weakref)
        else:
            self._subscriptions[property].append(callback)

    def unsubscribe(self, weakref: WeakMethod) -> None:
        for subscr in self._weakmethod_subscriptions.values():
            with suppress(ValueError):
                subscr.remove(weakref)

    async def watch(self, property: str):
        async_event = self._watch_events.setdefault(property, Event())
        await async_event.wait()
