import asyncio
import inspect
import itertools
import logging

from functools import partial, wraps
from itertools import chain
from typing import Coroutine, Dict, Set, Tuple

import attrs


logger = logging.getLogger(__name__)


def ensure_coro_returns_tuple(coro):
    @wraps(coro)
    async def wrapper(*args, **kwargs):
        logger.debug(f"Starting execution of {coro.__name__}")
        match inspect.signature(coro).return_annotation:
            case tuple(_):
                res = await coro(*args, **kwargs)
            case _:
                res = (await coro(*args, **kwargs),)
        logger.debug(f"Finished execution of {coro.__name__}")
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
class Solution:
    edges: Tuple["Edge", ...] = attrs.field()
    known_nodes: Dict[str, asyncio.Future] = attrs.field(
        init=False,
        factory=dict,
    )

    def __attrs_post_init__(self):
        for out_ in itertools.chain(*(edge.outs for edge in self.edges)):
            assert (
                out_ not in self.known_nodes
            ), f"Duplicated out '{out_}' definition found in multiple edges"
            self.known_nodes.update({out_: asyncio.Future()})

    async def calculate_edge(self, edge: "Edge"):
        fn_args = await asyncio.gather(
            *(self.known_nodes[in_] for in_ in edge.ins)
        )
        results = dict(
            zip(
                edge.outs,
                await partial(edge.fn, *fn_args)(),
            )
        )
        for key, result in results.items():
            self.known_nodes[key].set_result(result)
        return results

    async def find(self):
        return await asyncio.gather(
            *(self.calculate_edge(edge) for edge in self.edges)
        )


@attrs.define(auto_attribs=True, frozen=True)
class Edge:
    fn: Coroutine = attrs.field(converter=ensure_coro_returns_tuple)
    ins: Tuple[str, ...] = attrs.field()
    outs: Tuple[str, ...] = attrs.field()

    @fn.validator
    def check_fn(self, _, fn):
        fn_sig = inspect.signature(ensure_coro_returns_tuple(fn))
        assert len(fn_sig.parameters) == len(self.ins), (
            f"Mismatch in {fn.__name__} arguments {fn_sig.parameters} "
            f"and ins definition {self.ins}"
        )
        assert len(fn_sig.return_annotation) == len(self.outs), (
            f"Mismatch in {fn.__name__} return args {fn_sig.return_annotation}"
            f" and outs definition {self.outs}"
        )


_Graph = set[Edge, ...]
_Solution = Tuple[Set[Edge], ...]


def resolve(graph: _Graph):
    def inner(
        known_nodes: Tuple[str, ...],
        edges_to_resolve: _Graph,
        result: _Solution,
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

    inner((), graph, (), 1)
