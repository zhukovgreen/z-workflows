import abc
import asyncio
import random

from typing import Any, Callable, ClassVar, Coroutine, List, Tuple, TypeVar

import attrs
import structlog

from aiocron import crontab
from structlog.contextvars import bind_contextvars, clear_contextvars

from z_workflows import graph


SENSOR_CHECK_INTERVAL = 5
WORKFLOW_TIMEOUT = 10

_EXECUTE_ON_SENSOR_ONCE = False

logger = structlog.getLogger()


@attrs.define(auto_attribs=True, frozen=True, slots=True)
class WorkflowBase:
    instances: ClassVar[List["_Workflow"]] = []

    id: str = attrs.field(init=False)

    ops: Tuple[graph.Edge, ...] = attrs.field()
    sensor: "_Sensor" = attrs.field()
    config: "_Config" = attrs.field()

    def __attrs_post_init__(self):
        WorkflowBase.instances.append(self)
        object.__setattr__(
            self,
            "id",
            f"{self.__class__.__name__}@{int(random.random() * 10000)}",
        )

    @ops.validator
    def check_ops(self, _, ops):
        graph.resolve(set(ops))

    async def execute(self) -> dict:
        logger.info(f"Starting workflow")
        results = await graph.Solution(edges=self.ops).find()
        logger.info(f"Finished workflow")
        return results

    async def execute_on_sensor(self) -> None:
        clear_contextvars()
        bind_contextvars(
            workflow_id=asyncio.current_task().get_name(),
            sensor_id=f"{self.sensor.__name__}@{int(random.random() * 10000)}",
        )
        while True:
            logger.info(f"Checking sensor {self.sensor.__name__}")
            if await self.sensor() is True:
                try:
                    await asyncio.wait_for(
                        self.execute(),
                        timeout=WORKFLOW_TIMEOUT,
                    )
                    if _EXECUTE_ON_SENSOR_ONCE:
                        break
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Workflow was cancelled after {WORKFLOW_TIMEOUT}s."
                    )
                    break
            else:
                logger.info(
                    f"Skipping task execution for {self.__class__.__name__} "
                    f"and wait..."
                )
            await asyncio.sleep(SENSOR_CHECK_INTERVAL)

    async def execute_on_schedule(self, schedule: str) -> None:
        clear_contextvars()
        bind_contextvars(
            workflow_id=asyncio.current_task().get_name(),
            schedule_id=f"{schedule}@{int(random.random() * 10000)}",
        )
        scheduled_task = crontab(schedule, func=self.execute, start=False)

        while True:
            await scheduled_task.next()


@attrs.define(auto_attribs=True, frozen=True, slots=True)
class ConfigBase(metaclass=abc.ABCMeta):
    ...


_Sensor = Callable[[], Coroutine[Any, Any, bool]]
_Workflow = TypeVar("_Workflow", bound=WorkflowBase)
_Config = TypeVar("_Config", bound=ConfigBase)
