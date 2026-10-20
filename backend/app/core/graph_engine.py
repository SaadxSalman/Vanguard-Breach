"""LangGraph-style state-graph orchestration engine.

Vanguard-Breach models its agent swarm as an explicit directed graph of
``(state) -> state`` node functions, mirroring LangGraph's StateGraph API
(nodes, static edges, conditional edges, entry/finish points, compiled
execution with step tracing and loop guards) without the heavy dependency
chain — so the platform runs on any Python 3.12+ install.
"""
from __future__ import annotations

import inspect
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

NodeFn = Callable[[dict[str, Any]], Any]
RouterFn = Callable[[dict[str, Any]], str]


class GraphError(RuntimeError):
    pass


@dataclass
class NodeTrace:
    node: str
    started_at: float
    finished_at: float = 0.0
    status: str = "running"
    detail: str = ""

    @property
    def duration_ms(self) -> float:
        return round((self.finished_at - self.started_at) * 1000, 2)


@dataclass
class RunTrace:
    nodes: list[NodeTrace] = field(default_factory=list)
    order: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "order": self.order,
            "nodes": [
                {"node": t.node, "status": t.status, "duration_ms": t.duration_ms,
                 "detail": t.detail}
                for t in self.nodes
            ],
        }


class StateGraph:
    """Declarative agent workflow. See :class:`CompiledGraph` for execution."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._nodes: dict[str, NodeFn] = {}
        self._edges: dict[str, str] = {}
        self._conditional: dict[str, tuple[RouterFn, dict[str, str]]] = {}
        self._entry: str | None = None
        self._finish: set[str] = set()

    def add_node(self, name: str, fn: NodeFn) -> "StateGraph":
        if name in self._nodes:
            raise GraphError(f"node '{name}' already registered")
        self._nodes[name] = fn
        return self

    def add_edge(self, source: str, target: str) -> "StateGraph":
        self._edges[source] = target
        return self

    def add_conditional_edges(self, source: str, router: RouterFn,
                              path_map: dict[str, str]) -> "StateGraph":
        self._conditional[source] = (router, path_map)
        return self

    def set_entry_point(self, name: str) -> "StateGraph":
        self._entry = name
        return self

    def set_finish_point(self, name: str) -> "StateGraph":
        self._finish.add(name)
        return self

    def compile(self, max_steps: int = 64) -> "CompiledGraph":
        if not self._entry:
            raise GraphError("entry point not set")
        if not self._nodes:
            raise GraphError("graph has no nodes")
        return CompiledGraph(self, max_steps=max_steps)


class CompiledGraph:
    def __init__(self, graph: StateGraph, max_steps: int) -> None:
        self.graph = graph
        self.max_steps = max_steps

    def _next(self, current: str, state: dict[str, Any]) -> str | None:
        if current in self.graph._finish:
            return None
        if current in self.graph._conditional:
            router, path_map = self.graph._conditional[current]
            key = router(state)
            target = path_map.get(key)
            if target is None:
                raise GraphError(f"router returned unknown path '{key}' from '{current}'")
            return target
        target = self.graph._edges.get(current)
        if target is None:
            raise GraphError(f"no outgoing edge from node '{current}'")
        return target

    async def run(self, state: dict[str, Any], trace: RunTrace | None = None,
                  on_node_done: Callable[[str, dict[str, Any]], Awaitable[None] | None] | None = None,
                  ) -> dict[str, Any]:
        trace = trace or RunTrace()
        current = self.graph._entry
        steps = 0
        while current is not None:
            if steps >= self.max_steps:
                raise GraphError(f"max_steps ({self.max_steps}) exceeded — cycle in graph?")
            steps += 1
            fn = self.graph._nodes[current]
            record = NodeTrace(node=current, started_at=time.time())
            trace.nodes.append(record)
            trace.order.append(current)
            try:
                result = fn(state)
                if inspect.isawaitable(result):
                    result = await result
                if isinstance(result, dict):
                    state.update(result)
                record.status = "ok"
            except Exception as exc:  # noqa: BLE001 - node errors are surfaced to run state
                record.status = "error"
                record.detail = f"{type(exc).__name__}: {exc}"
                record.finished_at = time.time()
                state["error"] = record.detail
                state["error_node"] = current
                state["trace"] = trace.to_dict()
                raise
            record.finished_at = time.time()
            if on_node_done:
                maybe = on_node_done(current, state)
                if inspect.isawaitable(maybe):
                    await maybe
            current = self._next(current, state)
        state["trace"] = trace.to_dict()
        return state
