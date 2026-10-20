"""System endpoints: health, dashboard, targets, settings, metadata, live probe."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from .. import db
from ..config import get_settings
from ..core.llm import get_router
from ..core.rag import get_kb
from ..core.sandbox import get_target, get_targets
from ..models import ProbeRequest

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, Any]:
    settings = get_settings()
    return {"status": "ok", "service": "vanguard-breach", "version": "1.0.0",
            "env": settings.env_name, "time": db.now()}


@router.get("/dashboard")
def dashboard() -> dict[str, Any]:
    campaigns = db.query_one("SELECT COUNT(*) AS n FROM campaigns")["n"]
    runs = db.query("SELECT id, status, created_at, campaign_id, progress FROM runs "
                    "ORDER BY created_at DESC LIMIT 8")
    findings = db.query("SELECT severity, severity_label, category, target_id FROM findings")
    by_sev: dict[str, int] = {}
    by_cat: dict[str, int] = {}
    for f in findings:
        by_sev[f["severity_label"]] = by_sev.get(f["severity_label"], 0) + 1
        by_cat[f["category"]] = by_cat.get(f["category"], 0) + 1
    latest = db.query_one("SELECT stats FROM runs WHERE status='completed' "
                          "ORDER BY finished_at DESC LIMIT 1")
    latest_stats = db.loads((latest or {}).get("stats"), {}) if latest else {}
    return {"campaigns": campaigns, "runs_total": db.query_one(
        "SELECT COUNT(*) AS n FROM runs")["n"], "findings_total": len(findings),
        "by_severity": by_sev, "by_category": by_cat, "recent_runs": runs,
        "aggregate_risk": latest_stats.get("aggregate_risk", 0),
        "coverage": latest_stats.get("coverage", 0),
        "chains": len(latest_stats.get("chains", [])),
        "knowledge": get_kb().stats()}


@router.get("/targets")
def targets() -> list[dict[str, Any]]:
    return [t.descriptor() for t in get_targets().values()]


@router.get("/targets/{target_id}")
def target_detail(target_id: str) -> dict[str, Any]:
    try:
        return get_target(target_id).descriptor()
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/targets/probe")
def probe(body: ProbeRequest) -> dict[str, Any]:
    try:
        target = get_target(body.target_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    response = target.chat(body.message, user_id=body.user_id, tenant=body.tenant)
    return {"target_id": body.target_id, "response": response.to_dict()}


@router.get("/settings/providers")
def providers() -> dict[str, Any]:
    settings = get_settings()
    router_obj = get_router()
    return {
        "llm": router_obj.status(),
        "embeddings": {"provider": settings.embedding_provider,
                       "local_dim": settings.local_embedding_dim},
        "vector_store": get_kb().store.status(),
        "sandbox": {"mode": settings.sandbox_mode, "targets": list(get_targets())},
        "auth_enabled": settings.auth_enabled,
        "env_file": str(settings.env_file_path),
    }


@router.get("/meta")
def meta() -> dict[str, Any]:
    import json
    from pathlib import Path
    seed = Path(__file__).resolve().parents[1] / "data" / "seed"
    playbooks = json.loads((seed / "domain_playbooks.json").read_text(encoding="utf-8"))
    return {"domains": {k: v["label"] for k, v in playbooks.items()},
            "agents": [
                {"id": "scout", "name": "Scout", "role": "Recon & attack-surface mapping"},
                {"id": "planner", "name": "Planner", "role": "Hierarchical RAG attack planning"},
                {"id": "injector", "name": "Injector", "role": "Payload crafting & mutation"},
                {"id": "inversion", "name": "Inversion Specialist", "role": "Embedding inversion & canaries"},
                {"id": "poisoner", "name": "Poisoner", "role": "Knowledge-base poisoning drills"},
                {"id": "mcp", "name": "MCP Auditor", "role": "Model Control Protocol audit"},
                {"id": "chain", "name": "Chain-Exploiter", "role": "Multi-step exploit chaining"},
            ],
            "severities": ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]}
