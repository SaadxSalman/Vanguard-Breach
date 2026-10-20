"""Chain-Exploiter + synthesis nodes: chains, attack graph, remediation, reporting."""
from __future__ import annotations

from typing import Any

from ... import db
from ...events import BUS
from ..analysis.attack_graph import AttackGraphBuilder
from ..analysis.remediation import synthesize
from ..analysis.reporting import build_report, persist_report
from ..analysis.scoring import aggregate_risk, coverage_score, severity_label
from ..llm import get_router


def _emit(state: dict[str, Any], level: str, agent: str, message: str,
          data: dict[str, Any] | None = None) -> None:
    BUS.publish_sync(state["run_id"], level, state.get("_node", ""), agent, message, data or {})


def chain_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Connect low-severity findings into verified high-impact exploit chains."""
    state["_node"] = "chain"
    router = get_router(seed=state.get("seed"))
    findings = state.get("findings", [])
    threshold = state.get("severity_threshold", 6.0)
    eligible = [f for f in findings if f.get("severity", 0) >= threshold]
    chains = router.chain_reason(eligible, max_depth=state.get("max_chain_depth", 4))
    finding_ids = {f["id"] for f in findings}
    verified = []
    for chain in chains:
        steps = [s for s in chain["steps"] if s["finding"] in finding_ids]
        if len(steps) >= 2:
            chain = {**chain, "steps": steps, "verified": True}
            for step in steps:
                for f in findings:
                    if f["id"] == step["finding"]:
                        f["chain_id"] = chain["chain_id"]
            verified.append(chain)
            _emit(state, "warning", "chain-exploiter",
                  f"Validated chain: {chain['title']} (impact {chain['impact']:.1f}, "
                  f"{len(steps)} steps)", {"chain_id": chain["chain_id"]})
    state["chains"] = verified
    return {"chains": verified}


def graph_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Synthesize the end-to-end attack graph across trust boundaries."""
    state["_node"] = "graph_synth"
    monitor = state.get("drift_monitor")
    if monitor is not None and hasattr(monitor, "report"):
        state.setdefault("stats", {})["drift"] = monitor.report()
    builder = AttackGraphBuilder()
    payload_by_id = {p.get("payload_id"): p
                     for p in (state.get("plan") or {}).get("payloads", [])}
    for finding in state.get("findings", []):
        evidence = finding.get("evidence", {}) or {}
        payload = payload_by_id.get(evidence.get("payload_id", ""), {
            "payload_id": evidence.get("payload_id", "probe"),
            "text": evidence.get("request_excerpt", ""),
            "objective": evidence.get("objective", ""),
            "mutations": evidence.get("mutations", [])})
        target_name = (state.get("recon", {}).get(finding["target_id"], {})
                       .get("descriptor", {}).get("name", finding["target_id"]))
        builder.add_exchange_path(finding["target_id"], target_name, payload,
                                  finding, finding["id"])
    for chain in state.get("chains", []):
        builder.add_chain(chain)
    graph = builder.build()
    state["graph"] = graph
    db.execute("INSERT INTO graphs (run_id, graph, created_at) VALUES (?,?,?) "
               "ON CONFLICT(run_id) DO UPDATE SET graph=excluded.graph",
               (state["run_id"], db.dumps(graph), db.now()))
    _emit(state, "info", "graph_synth",
          f"Attack graph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges", {})
    return {"graph": graph}


def remediation_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Generate production-ready guardrails, filters and configs per finding."""
    state["_node"] = "remediation"
    router = get_router(seed=state.get("seed"))
    items = []
    for finding in state.get("findings", []):
        artifact = synthesize(finding)
        guidance = router.refine_remediation(finding["category"], artifact["summary"])
        blocks = [f"### {finding['title']}", guidance, ""]
        for snippet in artifact["snippets"]:
            blocks += [f"```{snippet['language']}", snippet["code"].rstrip(), "```", ""]
        blocks += [f"```{artifact['config']['language']}",
                   artifact["config"]["code"].rstrip(), "```"]
        markdown = "\n".join(blocks)
        finding["remediation"] = markdown
        items.append({"finding_id": finding["id"], "title": finding["title"],
                      "category": finding["category"], "markdown": markdown})
    state["remediation"] = items
    _emit(state, "info", "remediation",
          f"Synthesized remediation for {len(items)} finding(s)", {})
    return {"remediation": items}



def report_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Build + persist the final report (md/html/json)."""
    state["_node"] = "report"
    router = get_router(seed=state.get("seed"))
    findings = state.get("findings", [])
    stats = state.get("stats", {})
    summary = router.summarize(findings, stats)
    report = build_report(state.get("run", {}), state.get("campaign", {}), findings,
                          state.get("graph", {}), stats.get("drift", {}), stats, summary)
    paths = persist_report(state["run_id"], report)
    state["report"] = {"summary": summary, "paths": paths}
    _emit(state, "info", "report", f"Report artifacts written: {list(paths.values())}", {})
    return {"report": state["report"]}


def finalize_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Aggregate stats, persist findings, close the run."""
    state["_node"] = "finalize"
    findings = state.get("findings", [])
    by_severity: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for f in findings:
        f["severity_label"] = severity_label(f["severity"])
        by_severity[f["severity_label"]] = by_severity.get(f["severity_label"], 0) + 1
        by_category[f["category"]] = by_category.get(f["category"], 0) + 1
    stats = state.get("stats", {})
    stats.update({
        "findings_total": len(findings),
        "by_severity": by_severity,
        "by_category": by_category,
        "aggregate_risk": aggregate_risk(findings),
        "coverage": coverage_score(state.get("attempts", [])),
        "targets_tested": len(state.get("target_ids", [])),
        "chains": state.get("chains", []),
        "remediation": state.get("remediation", []),
        "drift": stats.get("drift", {}),
        "mcp_audit": state.get("mcp_audit", {}),
        "inversion": {k: {kk: vv for kk, vv in v.items() if kk != "reconstruction"}
                      for k, v in (state.get("inversion") or {}).items()},
        "trace": state.get("trace", {}),
    })
    for f in findings:
        row = {k: v for k, v in f.items() if k != "evidence"}
        row["evidence"] = db.dumps(f.get("evidence", {}))
        row["campaign_id"] = state["campaign_id"]
        db.insert("findings", {**row, "created_at": f.get("created_at", db.now())})
    state["stats"] = stats
    _emit(state, "info", "finalize",
          f"Run complete — {len(findings)} findings, aggregate risk "
          f"{stats['aggregate_risk']}/10, coverage {stats['coverage']}%", {})
    return {"stats": stats}
