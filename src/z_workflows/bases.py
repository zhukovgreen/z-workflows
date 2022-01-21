import abc
import asyncio
import inspect
import logging

from typing import Any, Callable, ClassVar, Coroutine, Dict, Tuple, TypeVar

import attrs

from z_workflows import graph


logger = logging.getLogger(__name__)

_FnName = str
_FnSignature = inspect.Signature
_FnOutsNames = Tuple[str, ...]
_WorkflowName = str
_Op = Coroutine
_Sensor = Callable[[], Coroutine[Any, Any, bool]]


@attrs.define(auto_attribs=True)
class WorkflowBase(metaclass=abc.ABCMeta):
    registry: ClassVar[Dict[_WorkflowName, "_Workflow"]] = {}
    ops: Tuple[graph.Edge, ...] = attrs.field()

    @ops.validator
    def check_ops(self, _, ops):
        graph.resolve(set(ops))

    async def execute(self) -> dict:
        logger.info(f"Executing workflow {self.__class__.__name__}")
        results = await graph.Solution(edges=self.ops).find()
        logger.info(f"Workflow {self.__class__.__name__} finished")
        return results

    async def execute_on_sensor(self, sensor: _Sensor) -> dict:
        await sense(self.execute, sensor)


@attrs.define(auto_attribs=True)
class ConfigBase(metaclass=abc.ABCMeta):
    ...


_Workflow = TypeVar("_Workflow", bound=WorkflowBase)
_Config = TypeVar("_Config", bound=ConfigBase)


async def sense(coro: Callable[[], Coroutine], sensor: _Sensor) -> None:
    while True:
        logger.debug(f"Checking sensor {sensor.__name__}")
        if await sensor() is True:
            logger.info(f"Executing workflow {coro}")
            task = asyncio.create_task(coro())
            await task
        else:
            logger.debug(f"Skipping task execution and wait...")
        await asyncio.sleep(5)
