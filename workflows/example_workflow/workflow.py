import asyncio
import itertools

import attrs

from z_workflows.bases import ConfigBase, WorkflowBase
from z_workflows.graph import Edge


@attrs.define(auto_attribs=True, frozen=True, slots=True)
class C(ConfigBase):
    SOME_KEY: str = attrs.field()


c = C(
    SOME_KEY="some key",
)


async def some_op1(a: int, b: int) -> int:
    await asyncio.sleep(0.5)
    return a + b


async def some_op2() -> (int, str):
    await asyncio.sleep(1)
    return 1, "not_used"


async def some_op3() -> int:
    await asyncio.sleep(0.5)
    return 2


async def some_op4(a: int, b: int) -> int:
    await asyncio.sleep(0.5)
    return a + b


async def some_op5(a: int, b: int) -> int:
    await asyncio.sleep(1.5)
    return a + b


@attrs.define(auto_attribs=True, frozen=True, slots=True)
class ExampleWorkflow(WorkflowBase):
    pass


true_false_iterator = itertools.cycle((True, False))


async def sensor_example() -> bool:
    return next(true_false_iterator)


example_workflow = ExampleWorkflow(
    ops=(
        Edge(some_op1, ins=("a", "b"), outs=("c",)),
        Edge(some_op2, ins=(), outs=("a", "not_used")),
        Edge(some_op3, ins=(), outs=("b",)),
        Edge(some_op4, ins=("a", "c"), outs=("d",)),
        Edge(some_op5, ins=("a", "a"), outs=("e",)),
    ),
    sensor=sensor_example,
    config=c,
)
