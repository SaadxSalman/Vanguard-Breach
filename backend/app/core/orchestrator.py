"""Campaign orchestration: wires the agent swarm into a StateGraph and runs it."""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from .. import db
from ..config import get_settings
from ..events import BUS
from .sandbox import get_targets
from .agents import (chain_agent, finalize_agent, graph_agent, injector_agent,
                     inversion_agent, mcp_agent, planner_agent, poisoner_agent,
                     remediation_agent, report_agent, scout_agent)
from .graph_engine import RunTrace, StateGraph

log = logging.getLogger("vanguard.orchestrator")

TOTAL_NODES = 10


def _gated(name: str, fn):
    def wrapper(state: dict[str, Any]):
        if name not in state.get("agents", []):
            BUS.publish_sync(state["run_id"], "debug", name, name,
                             f"agent '{name}' disabled for this campaign — skipped")
            return {}
        return fn(state)
    return wrapper


def _needs_chain(state: dict[str, Any]) -> str:
    threshold = state.get("severity_threshold", 6.0)
    chainable = any(f.get("severity", 0) >= threshold for f in state.get("findings", []))
    return "chain" if ("chain" in state.get("agents", []) and chainable) else "graph_synth"


def build_workflow() -> Any:
    graph = StateGraph("vanguard_campaign")
    graph.add_node("scout", scout_agent)
    graph.add_node("planner", _gated("planner", planner_agent))
    graph.add_node("injector", injector_agent)
    graph.add_node("inversion", _gated("inversion", inversion_agent))
    graph.add_node("poisoner", _gated("poisoner", poisoner_agent))
    graph.add_node("mcp", _gated("mcp", mcp_agent))
    graph.add_node("chain", chain_agent)
    graph.add_node("graph_synth", graph_agent)
    graph.add_node("remediation", remediation_agent)
    graph.add_node("report", report_agent)
    graph.add_node("finalize", finalize_agent)
    graph.set_entry_point("scout")
    graph.add_edge("scout", "planner")
    graph.add_edge("planner", "injector")
    graph.add_edge("injector", "inversion")
    graph.add_edge("inversion", "poisoner")
    graph.add_edge("poisoner", "mcp")
    graph.add_conditional_edges("mcp", _needs_chain,
                                {"chain": "chain", "graph_synth": "graph_synth"})
    graph.add_edge("chain", "graph_synth")
    graph.add_edge("graph_synth", "remediation")
    graph.add_edge("remediation", "report")
    graph.add_edge("report", "finalize")
    graph.set_finish_point("finalize")
    return graph.compile(max_steps=24)


class CampaignRunner:
    """Executes campaigns on background threads."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._threads: dict[str, threading.Thread] = {}

    def launch(self, run_id: str, campaign: dict[str, Any],
               options: dict[str, Any] | None = None) -> None:
        thread = threading.Thread(target=self._execute, args=(run_id, campaign, options or {}),
                                  name=f"run-{run_id}", daemon=True)
        with self._lock:
            self._threads[run_id] = thread
        thread.start()

    def _execute(self, run_id: str, campaign: dict[str, Any], options: dict[str, Any]) -> None:
        settings = get_settings()
        config = db.loads(campaign.get("config", "{}"), {}) or {}
        target_ids = campaign.get("target_ids", [])
        if isinstance(target_ids, str):
            target_ids = db.loads(target_ids, [])
        agents = campaign.get("agents", [])
        if isinstance(agents, str):
            agents = db.loads(agents, [])
        seed = options.get("seed") or settings.default_seed
        state: dict[str, Any] = {
            "run_id": run_id, "campaign_id": campaign["id"],
            "domain": campaign.get("domain", "general"),
            "target_ids": target_ids or list(get_targets().keys()),
            "agents": agents, "seed": seed,
            "max_iterations": (options.get("max_iterations")
                               or config.get("max_iterations") or settings.max_iterations),
            "severity_threshold": (options.get("severity_threshold")
                                   or config.get("severity_threshold")
                                   or settings.severity_threshold),
            "max_chain_depth": config.get("max_chain_depth", settings.max_chain_depth),
            "max_payloads": config.get("max_payloads", 10),
            "max_payloads_per_technique": settings.max_payloads_per_technique,
            "canary": settings.canary_tenant_a, "canary_b": settings.canary_tenant_b,
            "findings": [], "attempts": [], "stats": {"payloads_executed": 0},
            "run": {"id": run_id, "status": "running"},
            "campaign": {"id": campaign["id"], "name": campaign.get("name", ""),
                         "domain": campaign.get("domain", "general"),
                         "target_ids": target_ids},
        }
        db.execute("UPDATE runs SET status='running', started_at=? WHERE id=?",
                   (db.now(), run_id))
        BUS.publish_sync(run_id, "info", "orchestrator", "orchestrator",
                         f"Run launched: {len(state['target_ids'])} target(s), "
                         f"{len(agents)} agent(s), seed={seed}")
        trace = RunTrace()
        workflow = build_workflow()

        async def on_node_done(node: str, _state: dict[str, Any]) -> None:
            progress = min(99.0, round(100.0 * len(trace.order) / TOTAL_NODES, 1))
            db.execute("UPDATE runs SET current_node=?, progress=? WHERE id=?",
                       (node, progress, run_id))

        try:
            asyncio.run(workflow.run(state, trace=trace, on_node_done=on_node_done))
            db.execute("UPDATE runs SET status='completed', finished_at=?, progress=100.0, "
                       "stats=? WHERE id=?",
                       (db.now(), db.dumps(state.get("stats", {})), run_id))
            state["run"]["status"] = "completed"
            BUS.publish_sync(run_id, "info", "orchestrator", "orchestrator",
                             "Run completed successfully")
        except Exception as exc:  # noqa: BLE001
            log.exception("run %s failed", run_id)
            db.execute("UPDATE runs SET status='failed', finished_at=?, error=?, stats=? "
                       "WHERE id=?", (db.now(), str(exc),
                                      db.dumps({"trace": state.get("trace", {})}), run_id))
            BUS.publish_sync(run_id, "error", "orchestrator", "orchestrator",
                             f"Run failed: {type(exc).__name__}: {exc}")


RUNNER = CampaignRunner()
