import asyncio
import inspect
import logging

from functools import partial, wraps
from itertools import chain
from typing import Coroutine, Set, Tuple

import attrs
import pytest


logger = logging.getLogger(__name__)


def ensure_coro_returns_tuple(coro):
    @wraps(coro)
    async def wrapper(*args, **kwargs):
        logger.debug(f"    Starting execution of {coro.__name__}")
        match inspect.signature(coro).return_annotation:
            case tuple(_):
                res = await coro(*args, **kwargs)
            case _:
                res = (await coro(*args, **kwargs),)
        logger.debug(f"    Finished execution of {coro.__name__}")
        return res

    assert inspect.iscoroutinefunction(
        coro
    ), f"{coro.__name__} should be a coroutine."
    sig = inspect.signature(coro)
    if not isinstance(sig.return_annotation, tuple):
        sig = sig.replace(return_annotation=(sig.return_annotation,))
        wrapper.__signature__ = sig
    return wrapper


@attrs.define(auto_attribs=True, frozen=True)
class Edge:
    fn: Coroutine = attrs.field(converter=ensure_coro_returns_tuple)
    ins: Tuple[str, ...] = attrs.field()
    outs: Tuple[str, ...] = attrs.field()

    @fn.validator
    def check_fn(self, attrib, fn):
        fn_sig = inspect.signature(ensure_coro_returns_tuple(fn))
        assert len(fn_sig.parameters) == len(self.ins), (
            f"Mismatch in {fn.__name__} arguments number and ins definition "
            f"{self.ins}"
        )
        assert len(fn_sig.return_annotation) == len(self.outs), (
            f"Mismatch in {fn.__name__} return args and outs definition "
            f"{self.outs}"
        )


_Graph = set[Edge, ...]
Solution = Tuple[Set[Edge], ...]


def resolve(graph: _Graph) -> Solution:
    def inner(
        known_nodes: Tuple[str, ...],
        edges_to_resolve: _Graph,
        result: Solution,
        epoch: int,
    ):
        logger.debug(
            f"""
            Epoch {epoch}:
            Known nodes: {known_nodes}
            Not resolved: {edges_to_resolve}
            Already resolved: {result}
            """
        )
        if not edges_to_resolve:
            return result

        solved_edges = set(
            filter(
                lambda edge: (
                    all(node in known_nodes for node in edge.ins)
                    or edge.ins == ()
                ),
                edges_to_resolve,
            )
        )
        if not solved_edges:
            raise ValueError("Can't solve the graph.")
        else:
            return inner(
                known_nodes
                + tuple(
                    chain.from_iterable((edge.outs for edge in solved_edges))
                ),
                edges_to_resolve - solved_edges,
                result + (solved_edges,),
                epoch + 1,
            )

    return inner((), graph, (), 1)


async def execute(solution: Solution) -> dict:
    async def inner(args_registry, group, epoch, groups_to_resolve) -> dict:
        await asyncio.sleep(0)
        logger.debug(f"Executing epoch: {epoch}")
        results = await asyncio.gather(
            *(
                partial(
                    edge.fn,
                    *(args_registry.get(node) for node in edge.ins),
                )()
                for edge in group
            )
        )
        for keys, values in zip((edge.outs for edge in group), results):
            assert not any(key in args_registry for key in keys), (
                f"Duplicated out key found in the group. "
                f"Already known keys: {args_registry}\n"
                f"Keys trying to add: {dict(zip(keys, values))}"
            )
            args_registry.update(zip(keys, values))
        if not groups_to_resolve:
            return args_registry
        return await inner(
            args_registry,
            groups_to_resolve[0],
            epoch + 1,
            groups_to_resolve[1:],
        )

    if not solution:
        return {}
    return await inner(
        {},
        solution[0],
        1,
        solution[1:],
    )


@pytest.mark.asyncio
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
        await asyncio.sleep(0.5)
        return a + b

    some_graph = {
        Edge(some_op1, ins=("a", "b"), outs=("c",)),
        Edge(some_op2, ins=(), outs=("a", "not_used")),
        Edge(some_op3, ins=(), outs=("b",)),
        Edge(some_op4, ins=("a", "c"), outs=("d",)),
        Edge(some_op5, ins=("a", "a"), outs=("h",)),
    }
    actual = await execute(resolve(some_graph))
    expected = {
        "a": 1,
        "b": 2,
        "c": 3,
        "d": 4,
        "h": 2,
        "not_used": "not_used",
    }

    assert actual == expected
