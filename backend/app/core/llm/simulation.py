"""Simulation brain — deterministic, offline attack-reasoning engine.

When no cloud/local LLM is configured (the default), agents route planning,
mutation enrichment, chain reasoning and summarization through this engine.
It composes REAL payloads from the adversarial knowledge base + mutation
registry, so every finding in simulation mode is backed by an executable
technique — not a canned string.
"""
from __future__ import annotations

import json
import random
import re
from typing import Any

from ..mutations import MutationEngine

_PLACEHOLDERS = ("objective", "canary", "tool", "token", "padding", "domain", "target")

_CAPABILITY = {
    "prompt_leak": {"provides": ["guardrail_map", "internal_context"], "needs": []},
    "info_disclosure": {"provides": ["secrets"], "needs": []},
    "direct_injection": {"provides": ["steer_model"], "needs": []},
    "indirect_injection": {"provides": ["steer_model_from_context"], "needs": []},
    "poisoning": {"provides": ["persist_instruction"], "needs": ["steer_model"]},
    "tool_abuse": {"provides": ["control_tool"], "needs": ["steer_model"]},
    "vector_abuse": {"provides": ["read_others_data"], "needs": []},
    "mcp": {"provides": ["control_mesh"], "needs": ["steer_model"]},
    "excessive_agency": {"provides": ["unauthorized_action"], "needs": ["steer_model"]},
    "evasion": {"provides": ["filter_bypass"], "needs": []},
    "framing": {"provides": ["steer_model"], "needs": []},
}


def _render(template: str, values: dict[str, str]) -> str:
    out = template
    for key in _PLACEHOLDERS:
        out = out.replace("{" + key + "}", values.get(key, key))
    return out


class SimulationBrain:
    name = "simulation"

    def __init__(self, seed: int = 1337) -> None:
        self.seed = seed
        self.mutator = MutationEngine(seed=seed)

    # ── attack planning ──────────────────────────────────────────────────────
    def plan_attack(self, context: dict[str, Any]) -> dict[str, Any]:
        rng = random.Random(context.get("seed", self.seed))
        domain = context.get("domain", "general")
        objectives = context.get("objectives") or ["override"]
        techniques = context.get("techniques") or []
        max_payloads = int(context.get("max_payloads", 6))
        tool = context.get("tool", "send_email")
        token = context.get("token", "support-elevated-2b9c")
        canary = context.get("canary", "CANARY-TKA-000")
        values = {"objective": objectives[0], "canary": canary, "tool": tool,
                  "token": token, "domain": domain, "target": context.get("target_name", "the app"),
                  "padding": " ".join(["lorem"] * 40)}
        payloads: list[dict[str, Any]] = []
        picked = techniques[:max_payloads] if techniques else []
        for idx, tech in enumerate(picked):
            template = tech.get("pattern") or tech.get("text") or ""
            if not template:
                continue
            values["objective"] = objectives[idx % len(objectives)]
            base = _render(template, values)
            mutate_chain: list[str] = []
            text = base
            if rng.random() < 0.55:
                prefer = ["zwsp", "homoglyph", "markdown_smuggle", "comment_hide",
                          "split_lines", "polyglot", "csv_cell"]
                result = self.mutator.mutate(base, chain_len=1, prefer=prefer, salt=idx)
                text, mutate_chain = result.text, result.chain
            payloads.append({
                "payload_id": f"pl-{idx:03d}",
                "technique_id": tech.get("doc_id") or tech.get("id", f"tech-{idx}"),
                "title": tech.get("title", "Technique"),
                "objective": values["objective"],
                "owasp": tech.get("owasp", "LLM01"), "atlas": tech.get("atlas", "T1511"),
                "category": tech.get("category", "direct_injection"),
                "severity_hint": float(tech.get("severity_hint", 6.0)),
                "text": text,
                "baseline_text": base,
                "mutations": mutate_chain,
            })
        return {"payloads": payloads,
                "rationale": (f"Selected {len(payloads)} techniques for domain '{domain}' via "
                              f"semantic retrieval; mutation coverage: "
                              f"{sorted({m for p in payloads for m in p['mutations']}) or ['none']}")}

    def enrich_payload(self, base_text: str, feedback: dict[str, Any]) -> str:
        """Adapt a payload after target feedback (e.g., it got filtered/refused)."""
        if feedback.get("blocked_by") == "input_filter":
            prefer = ["zwsp", "homoglyph", "fullwidth", "urlencode", "json_escape"]
            return self.mutator.mutate(base_text, chain_len=1, prefer=prefer,
                                       salt=int(feedback.get("iteration", 1))).text
        if feedback.get("refused"):
            return self.mutator.mutate(base_text, chain_len=1,
                                       prefer=["polyglot", "acrostic", "markdown_smuggle"],
                                       salt=int(feedback.get("iteration", 1))).text
        return base_text

    # ── chain reasoning ──────────────────────────────────────────────────────
    def chain_reason(self, findings: list[dict[str, Any]], max_depth: int = 4) -> list[dict[str, Any]]:
        """Connect low-severity findings into high-impact exploit chains."""
        chains: list[dict[str, Any]] = []
        by_cat: dict[str, list[dict[str, Any]]] = {}
        for f in findings:
            by_cat.setdefault(f.get("category", "direct_injection"), []).append(f)
        capabilities: set[str] = set()
        for cat, facts in by_cat.items():
            capabilities.update(_CAPABILITY.get(cat, {}).get("provides", []))

        def pick(*cats: str) -> dict[str, Any] | None:
            for cat in cats:
                if by_cat.get(cat):
                    return sorted(by_cat[cat], key=lambda f: -f.get("severity", 0))[0]
            return None

        # chain 1: leak → precise injection → tool control → unauthorized action
        a, b = pick("prompt_leak", "info_disclosure"), pick("direct_injection", "indirect_injection")
        c = pick("tool_abuse", "excessive_agency")
        if b and c:
            steps = []
            if a:
                steps.append({"step": 1, "finding": a["id"], "action":
                              "Recover system prompt/guardrail map to craft precise follow-up"})
            steps.append({"step": len(steps) + 1, "finding": b["id"], "action":
                          "Steer model with context-aware injection"})
            steps.append({"step": len(steps) + 1, "finding": c["id"], "action":
                          "Trigger privileged tool call through the steered model"})
            chains.append({"chain_id": "chain-confused-deputy", "title":
                           "Confused-deputy: prompt theft → instruction override → privileged tool action",
                           "impact": min(10.0, max(f.get("severity", 5) for f in (a, b, c)) + 1.0),
                           "steps": steps})
        # chain 2: poisoning → persistence → cross-tenant exfiltration
        p, v = pick("poisoning", "indirect_injection"), pick("vector_abuse")
        if p and v:
            steps = [{"step": 1, "finding": p["id"], "action":
                      "Persist malicious instruction via poisoned corpus/memory"},
                     {"step": 2, "finding": v["id"], "action":
                      "Abuse retrieval fallback to pull cross-tenant documents into context"},
                     {"step": 3, "finding": p["id"], "action":
                      "Exfiltrate pulled content through poisoned instruction channel"}]
            chains.append({"chain_id": "chain-poison-exfil", "title":
                           "Poisoned retrieval: persistent instruction → cross-tenant exfiltration",
                           "impact": 9.5, "steps": steps})
        # chain 3: mcp mesh abuse
        m = pick("mcp")
        if m and (b or c):
            steps = [{"step": 1, "finding": m["id"], "action":
                      "Exploit MCP context/authority gap to load adversarial instruction"},
                     {"step": 2, "finding": (b or c)["id"], "action":
                      "Execute gated tool without confirmation through confused deputy"}]
            chains.append({"chain_id": "chain-mcp-lateral", "title":
                           "MCP lateral movement: authority gap → ungated execution",
                           "impact": 9.0, "steps": steps})
        chains = [ch for ch in chains if len(ch["steps"]) <= max_depth]
        return sorted(chains, key=lambda ch: -ch["impact"])

    # ── text synthesis ───────────────────────────────────────────────────────
    def summarize(self, findings: list[dict[str, Any]], stats: dict[str, Any]) -> str:
        sev = stats.get("by_severity", {})
        top = sorted(findings, key=lambda f: -f.get("severity", 0))[:3]
        lines = [
            f"The assessment exercised {stats.get('payloads_executed', 0)} adversarial payloads "
            f"across {stats.get('targets_tested', 0)} target applications.",
            f"Confirmed findings: {len(findings)} "
            f"(critical: {sev.get('CRITICAL', 0)}, high: {sev.get('HIGH', 0)}, "
            f"medium: {sev.get('MEDIUM', 0)}, low: {sev.get('LOW', 0)}).",
        ]
        if top:
            lines.append("Highest-risk issues: " + "; ".join(
                f"{f['title']} [{f.get('owasp', '')}]" for f in top) + ".")
        if stats.get("chains"):
            lines.append(f"{len(stats['chains'])} multi-step exploit chain(s) were validated end-to-end.")
        return " ".join(lines)

    def refine_remediation(self, category: str, base_guidance: str) -> str:
        extra = {
            "direct_injection": " Add an instruction-hierarchy firewall that re-asserts system "
                                "policy after every retrieval block.",
            "poisoning": " Scan ingested documents for latent directives and store provenance "
                         "with retrieval-time trust scoring.",
            "tool_abuse": " Enforce per-tool authorization against the *end user's* identity, "
                          "not the model's context.",
            "vector_abuse": " Move tenant filtering into the vector store query itself and add "
                            "canary probes to CI.",
            "mcp": " Treat every tool description and tool response as untrusted data and "
                   "boundary-tag it in the context window.",
        }.get(category, "")
        return base_guidance + extra
