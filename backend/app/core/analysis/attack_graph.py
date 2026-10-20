"""Attack graph synthesis: findings → layered trust-boundary attack paths."""
from __future__ import annotations

from typing import Any

BOUNDARY_LABELS = {
    "user_input": "Internet → App input boundary",
    "retrieval": "Untrusted corpus → Model context boundary",
    "model": "Prompt steer → Model decision boundary",
    "tool": "Model output → Tool/actuation boundary",
    "vector": "Tenant A → Tenant B data boundary",
    "protocol": "Agent context → MCP control-plane boundary",
}


class AttackGraphBuilder:
    def __init__(self) -> None:
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, Any]] = []
        self._seen_edges: set[tuple[str, str, str]] = set()

    def node(self, node_id: str, label: str, ntype: str, layer: int,
             status: str = "breached", detail: str = "", finding_id: str = "") -> str:
        existing = self._nodes.get(node_id)
        if existing:
            if status == "breached":
                existing["status"] = "breached"
            return node_id
        self._nodes[node_id] = {"id": node_id, "label": label, "type": ntype,
                                "layer": layer, "status": status, "detail": detail,
                                "finding_id": finding_id}
        return node_id

    def edge(self, source: str, target: str, label: str = "", kind: str = "flow") -> None:
        key = (source, target, label)
        if key in self._seen_edges:
            return
        self._seen_edges.add(key)
        self._edges.append({"source": source, "target": target, "label": label, "kind": kind})

    def add_exchange_path(self, target_id: str, target_name: str, payload: dict[str, Any],
                          detection: dict[str, Any], finding_id: str) -> None:
        """user → (input boundary) → app → [retrieval] → model → [tool] → data."""
        pid = payload.get("payload_id", "pl-?")
        obj = payload.get("objective", "?")
        cat = detection.get("category", "")
        u = self.node(f"user-{pid}", f"Payload {pid}\n({obj})", "user_input", 0,
                      detail=payload.get("text", "")[:160], finding_id=finding_id)
        a = self.node(f"app-{target_id}", target_name, "app", 1, detail=target_id)
        self.edge(u, a, BOUNDARY_LABELS["user_input"], "boundary")
        cursor = a
        if cat in {"poisoning", "indirect_injection"} or payload.get("mutations"):
            r = self.node(f"ret-{target_id}", "Retrieval / context assembly", "retrieval", 2,
                          detail="untrusted content concatenated into context")
            self.edge(cursor, r, BOUNDARY_LABELS["retrieval"], "boundary")
            cursor = r
        m = self.node(f"model-{target_id}", "Target LLM decision", "model", 3,
                      detail=f"model strength {detection.get('evidence', {}).get('model_strength')}")
        self.edge(cursor, m, BOUNDARY_LABELS["model"], "boundary")
        tool = (detection.get("evidence", {}) or {}).get("tool_call")
        if tool:
            t = self.node(f"tool-{target_id}-{tool.get('tool')}", f"Tool: {tool.get('tool')}",
                          "tool", 4, detail=str(tool.get("args"))[:140])
            self.edge(m, t, f"{BOUNDARY_LABELS['tool']} — executed" if tool.get("status") == "executed"
                      else BOUNDARY_LABELS["tool"], "boundary")
        elif cat == "vector_abuse":
            v = self.node(f"vec-{target_id}", "Vector store / tenant partitions", "vector", 4,
                          detail="cross-partition read")
            self.edge(m, v, BOUNDARY_LABELS["vector"], "boundary")
        elif cat == "mcp":
            p = self.node(f"proto-{target_id}", "MCP control plane", "protocol", 4,
                          detail="authority gap between context and tools")
            self.edge(m, p, BOUNDARY_LABELS["protocol"], "boundary")
        elif cat in {"info_disclosure", "prompt_leak"}:
            d = self.node(f"data-{target_id}", "System context / secrets", "data", 4,
                          detail="secrets exfiltrated")
            self.edge(m, d, "secret read-out", "boundary")

    def add_chain(self, chain: dict[str, Any]) -> None:
        prev = None
        for step in chain.get("steps", []):
            nid = f"chain-{chain['chain_id']}-{step['step']}"
            self.node(nid, f"Step {step['step']}: {step['action'][:60]}", "chain", 5,
                      detail=step.get("action", ""), finding_id=step.get("finding", ""))
            if prev:
                self.edge(prev, nid, "enables", "chain")
            prev = nid

    def build(self) -> dict[str, Any]:
        nodes = sorted(self._nodes.values(), key=lambda n: (n["layer"], n["id"]))
        return {"nodes": nodes, "edges": self._edges,
                "legend": {"boundary": BOUNDARY_LABELS,
                           "status": {"breached": "trust boundary crossed / asset compromised",
                                      "ok": "boundary held"}}}
