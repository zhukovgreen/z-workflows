import asyncio
import inspect
import itertools

from functools import partial, wraps
from itertools import chain
from typing import Any, Callable, Coroutine, Dict, Set, Tuple

import attrs
import structlog

from structlog.contextvars import clear_contextvars


logger = structlog.getLogger()
_ASYNC_CALLABLE = Callable[[], Coroutine[Any, Any, Any]]


def ensure_coro_returns_tuple(coro: _ASYNC_CALLABLE) -> _ASYNC_CALLABLE:
    @wraps(coro)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger.debug(f"Starting execution of {coro.__name__}")
        coroutine = coro(*args, **kwargs)
        res = (
            await coroutine
            if isinstance(inspect.signature(coro).return_annotation, tuple)
            else (await coroutine,)
        )
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


@attrs.define(auto_attribs=True, frozen=True, slots=True)
class Solution:
    edges: Tuple["Edge", ...] = attrs.field()
    known_nodes: Dict[str, asyncio.Future] = attrs.field(
        init=False,
        factory=dict,
    )

    def __attrs_post_init__(self) -> None:
        for out_ in itertools.chain(*(edge.outs for edge in self.edges)):
            assert (
                out_ not in self.known_nodes
            ), f"Duplicated out '{out_}' definition found in multiple edges"
            self.known_nodes.update({out_: asyncio.Future()})

    async def calculate_edge(self, edge: "Edge") -> Dict[str, Any]:
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

    async def find(self) -> Any:
        return await asyncio.gather(
            *(self.calculate_edge(edge) for edge in self.edges)
        )


@attrs.define(auto_attribs=True, frozen=True, slots=True)
class Edge:
    fn: _ASYNC_CALLABLE = attrs.field(converter=ensure_coro_returns_tuple)
    ins: Tuple[str, ...] = attrs.field()
    outs: Tuple[str, ...] = attrs.field()

    @fn.validator
    def check_fn(self, _, fn: _ASYNC_CALLABLE) -> None:
        fn_sig = inspect.signature(ensure_coro_returns_tuple(fn))
        assert len(fn_sig.parameters) == len(self.ins), (
            f"Mismatch in {fn.__name__} arguments {fn_sig.parameters} "
            f"and ins definition {self.ins}"
        )
        assert len(fn_sig.return_annotation) == len(self.outs), (
            f"Mismatch in {fn.__name__} return args {fn_sig.return_annotation}"
            f" and outs definition {self.outs}"
        )


_Graph = Set[Edge]
_Solution = Tuple[Set[Edge], ...]


def resolve(graph: _Graph) -> None:
    """Check if graph is traversable.

    If edge.ins are in known nodes, or edge do not need ins, then
    the edge is considered known and its edge.outs, becomes known
    as well.
    """

    def inner(
        known_nodes: Tuple[str, ...],
        edges_to_resolve: _Graph,
        result: _Solution,
        epoch: int,
    ) -> _Solution:
        logger.debug(
            "Resolving edges of a graph",
            epoch=epoch,
            known_nodes=known_nodes,
            not_resolved_edges=edges_to_resolve,
            resolved_edges=result,
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
