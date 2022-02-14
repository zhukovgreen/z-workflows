import asyncio

from z_workflows.graph import Edge, Solution, resolve


async def test_graph():
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

    edges = (
        Edge(some_op1, ins=("a", "b"), outs=("c",)),
        Edge(some_op2, ins=(), outs=("a", "not_used")),
        Edge(some_op3, ins=(), outs=("b",)),
        Edge(some_op4, ins=("a", "c"), outs=("d",)),
        Edge(some_op5, ins=("a", "a"), outs=("e",)),
    )
    resolve(set(edges))
    actual_ = await Solution(edges=edges).find()
    actual = {}
    for sub_dict in actual_:
        actual.update(sub_dict)
    expected = {
        "e": 2,
        "a": 1,
        "not_used": "not_used",
        "d": 4,
        "c": 3,
        "b": 2,
    }

    assert actual == expected
