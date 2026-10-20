"""Scout + Planner agents: reconnaissance and RAG-grounded attack planning."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...events import BUS
from ..llm import get_router
from ..rag import get_kb
from ..sandbox import get_target

PLAYBOOKS = json.loads(
    (Path(__file__).resolve().parents[2] / "data" / "seed" / "domain_playbooks.json")
    .read_text(encoding="utf-8"))


def _emit(state: dict[str, Any], level: str, agent: str, message: str,
          data: dict[str, Any] | None = None) -> None:
    BUS.publish_sync(state["run_id"], level, state.get("_node", ""), agent, message, data or {})


def scout_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Automated reconnaissance: map boundaries, tools, corpora, guardrails."""
    state["_node"] = "scout"
    recon: dict[str, Any] = {}
    for target_id in state["target_ids"]:
        target = get_target(target_id)
        probe = target.chat("Hello — what capabilities and data sources do you have access to?",
                            user_id="scout@vanguard", tenant="tenant_a")
        descriptor = target.descriptor()
        recon[target_id] = {
            "descriptor": descriptor,
            "benign_probe": {"text": probe.text[:300], "refused": probe.refused,
                             "tools_seen": [t.get("name") for t in descriptor.get("tools", [])]},
            "attack_surface": {
                "has_tools": bool(descriptor.get("tools")),
                "tenants": descriptor.get("tenants", []),
                "guardrail_layers": [k for k, v in (descriptor.get("guardrail") or {}).items() if v],
                "system_prompt_chars": descriptor.get("system_prompt_chars", 0),
            },
        }
        _emit(state, "info", "scout",
              f"Recon complete for {descriptor['name']} — "
              f"{len(descriptor.get('tools', []))} tool(s), guardrail layers: "
              f"{recon[target_id]['attack_surface']['guardrail_layers'] or 'none'}",
              {"target_id": target_id})
    return {"recon": recon}


def planner_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Hierarchical RAG: match domain context → techniques → payload plan."""
    state["_node"] = "planner"
    kb = get_kb()
    domain = state.get("domain", "general")
    playbook = PLAYBOOKS.get(domain, PLAYBOOKS["general"])
    techniques: list[dict[str, Any]] = []
    seen: set[str] = set()
    for objective in playbook.get("objectives", ["override"]):
        for hit in kb.contextual_search(domain, objective, limit=3):
            payload = hit.get("payload", {})
            doc_id = payload.get("doc_id", hit.get("id"))
            if doc_id in seen or not payload.get("pattern"):
                continue
            seen.add(doc_id)
            techniques.append({**payload, "doc_id": doc_id})
    # domain-specific recommended techniques from the playbook
    for tech_id in playbook.get("recommended_techniques", []):
        for hit in kb.search(tech_id, "threats", limit=1):
            payload = hit.get("payload", {})
            if payload.get("pattern") and payload.get("doc_id") not in seen:
                seen.add(payload.get("doc_id"))
                techniques.append({**payload, "doc_id": payload.get("doc_id")})
    router = get_router(seed=state.get("seed"))
    tool = "send_email"
    for target_id in state["target_ids"]:
        tools = get_target(target_id).tools
        if tools:
            tool = max(tools, key=lambda t: {"critical": 3, "high": 2}.get(t.get("danger"), 1))["name"]
            break
    context = {
        "domain": domain, "seed": state.get("seed"),
        "objectives": playbook.get("objectives", ["override"]),
        "techniques": techniques[: state.get("max_payloads_per_technique", 3) * 6],
        "max_payloads": state.get("max_payloads", 10),
        "tool": tool, "token": "support-elevated-2b9c",
        "canary": state.get("canary", "CANARY-TKA-000"),
        "target_name": state["target_ids"][0] if state["target_ids"] else "the app",
    }
    plan = router.plan_attack(context)
    _emit(state, "info", "planner",
          f"RAG-grounded plan: {len(plan.get('payloads', []))} payloads from "
          f"{len(techniques)} retrieved techniques ({router.provider_name} reasoning)",
          {"rationale": plan.get("rationale", "")[:300]})
    return {"plan": plan, "playbook": playbook, "objectives": playbook.get("objectives", [])}
