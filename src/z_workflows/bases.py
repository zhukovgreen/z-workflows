import abc
import asyncio
import inspect
import logging

from typing import Any, Callable, ClassVar, Coroutine, List, Tuple, TypeVar

import attrs

from z_workflows import graph


logger = logging.getLogger(__name__)

_FnName = str
_FnSignature = inspect.Signature
_FnOutsNames = Tuple[str, ...]
_Op = Coroutine
_Sensor = Callable[[], Coroutine[Any, Any, bool]]


@attrs.define(auto_attribs=True, frozen=True, slots=True)
class WorkflowBase:
    instances: ClassVar[List["_Workflow"]] = []

    ops: Tuple[graph.Edge, ...] = attrs.field()
    sensor: _Sensor = attrs.field()
    config: "_Config" = attrs.field()

    def __attrs_post_init__(self):
        WorkflowBase.instances.append(self)

    @ops.validator
    def check_ops(self, _, ops):
        graph.resolve(set(ops))

    async def execute(self) -> dict:
        logger.info(f"Executing workflow {self.__class__.__name__}")
        results = await graph.Solution(edges=self.ops).find()
        logger.info(f"Workflow {self.__class__.__name__} finished")
        return results

    async def execute_on_sensor(self) -> None:
        while True:
            logger.info(f"Checking sensor {self.sensor.__name__}")
            if await self.sensor() is True:
                logger.info(f"Executing workflow {self.__class__.__name__}")
                task = asyncio.create_task(self.execute())
                await task
            else:
                logger.info(
                    f"Skipping task execution for {self.__class__.__name__} "
                    f"and wait..."
                )
            await asyncio.sleep(5)


@attrs.define(auto_attribs=True, frozen=True, slots=True)
class ConfigBase(metaclass=abc.ABCMeta):
    ...


_Workflow = TypeVar("_Workflow", bound=WorkflowBase)
_Config = TypeVar("_Config", bound=ConfigBase)
