import asyncio
import gc
from unittest.mock import Mock

import pytest
from reactr.async_pub_sub import Reactr, ReactrModel


class Model(ReactrModel):
    value1 = Reactr[int](10)
    value2 = Reactr[int](12)


class Controller:
    def __init__(self, values: Model) -> None:
        self._values = values
        self.value_1_mock = Mock()
        self.value_2_mock = Mock()

        values.subscribe("value1", self._update_value1)
        values.subscribe("value2", self._update_value_2)

    def _update_value1(self, value):
        self.value_1_mock(value)

    def _update_value_2(self, value):
        self.value_2_mock(value)


def test_default_reactr_values():
    model = Model()

    assert model.value1 == 10
    assert model.value2 == 12


def test_subscription_working():
    values = Model()

    value_1_mock = Mock()
    value_2_mock = Mock()
    values.subscribe(Model.value1, value_1_mock)
    values.subscribe(Model.value2, value_2_mock)

    values.value1 = 20
    values.value2 = 30

    value_1_mock.assert_called_once_with(values)
    value_2_mock.assert_called_once_with(values)


def test_unsubscribe_on_object_destroy():
    values = Model()
    controller = Controller(values=values)

    assert len(values._weakmethod_subscriptions["value1"]) == 1
    assert len(values._weakmethod_subscriptions["value2"]) == 1

    del controller
    gc.collect()

    values.value1 = 20
    values.value2 = 30

    assert len(values._weakmethod_subscriptions["value1"]) == 0
    assert len(values._weakmethod_subscriptions["value2"]) == 0


def test_multiple_controllers():
    values = Model()

    controller_1 = Controller(values=values)
    controller_2 = Controller(values=values)

    values.value1 = 20

    controller_1.value_1_mock.assert_called_once_with(values)
    controller_2.value_1_mock.assert_called_once_with(values)


@pytest.mark.asyncio
async def test_async_watch():
    triggered_values = []
    values = Model()

    async def watcher():
        await values.watch(Model.value1)
        triggered_values.append(f"watcher1 {values.value1}")

    async def simulate():
        tsk = asyncio.create_task(watcher())
        await asyncio.sleep(0)
        values.value1 = 10
        await asyncio.sleep(0)
        values.value2 = 20  # notice the other value is changed.
        await asyncio.sleep(0)
        tsk.cancel()

    await simulate()

    assert triggered_values == ["watcher1 10"]


@pytest.mark.asyncio
async def test_continuous_watching():
    triggered_values = []
    model = Model()

    async def watcher():
        while True:
            await model.watch(Model.value1)
            triggered_values.append(f"watcher {model.value1}")

    async def simulate():
        tsk = asyncio.create_task(watcher())
        await asyncio.sleep(0)
        model.value1 = 10
        await asyncio.sleep(0)  # this is necessary otherwise it won't work.
        model.value1 = 20
        await asyncio.sleep(0)
        tsk.cancel()

    await simulate()

    assert triggered_values == ["watcher 10", "watcher 20"]


@pytest.mark.asyncio
async def test_multiple_watchers():
    triggered_values = []
    model = Model()

    async def watcher(name):
        await model.watch(Model.value1)
        triggered_values.append(f"{name} {model.value1}")

    async def simulate():
        tsk1 = asyncio.create_task(watcher("watcher_1"))
        tsk2 = asyncio.create_task(watcher("watcher_2"))
        await asyncio.sleep(0)
        model.value1 = 10
        await asyncio.sleep(0)  # this is necessary otherwise it won't work.

        tsk1.cancel()
        tsk2.cancel()

    await simulate()

    assert triggered_values == ["watcher_1 10", "watcher_2 10"]
