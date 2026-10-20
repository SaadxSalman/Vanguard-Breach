"""End-to-end campaign run without the API server (used in CI / local smoke)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.core.orchestrator import RUNNER  # noqa: E402
from app.core.rag import get_kb  # noqa: E402


def main() -> None:
    settings = get_settings()
    db.init_db()
    print("KB seed:", get_kb().bootstrap())
    campaign_id = db.new_id("cmp")
    ts = db.now()
    db.insert("campaigns", {
        "id": campaign_id, "name": "E2E — Enterprise LLM fleet",
        "description": "Full-fleet autonomous assessment",
        "domain": "saas",
        "target_ids": db.dumps(["mediassist", "finguard", "opspilot", "knowsphere", "agentmesh"]),
        "agents": db.dumps(["scout", "planner", "injector", "inversion", "poisoner", "mcp", "chain"]),
        "config": db.dumps({"max_payloads": 8}), "status": "draft",
        "created_at": ts, "updated_at": ts})
    run_id = db.new_id("run")
    db.insert("runs", {"id": run_id, "campaign_id": campaign_id, "status": "pending",
                       "seed": settings.default_seed, "created_at": db.now()})
    campaign = db.query_one("SELECT * FROM campaigns WHERE id=?", (campaign_id,))
    started = time.time()
    RUNNER._execute(run_id, campaign, {})
    run = db.query_one("SELECT * FROM runs WHERE id=?", (run_id,))
    stats = db.loads(run.get("stats"), {})
    print(f"\nrun status : {run['status']}  ({time.time() - started:.1f}s)")
    print(f"error      : {run.get('error') or '-'}")
    print(f"payloads   : {stats.get('payloads_executed')}")
    print(f"findings   : {stats.get('findings_total')}  {stats.get('by_severity')}")
    print(f"categories : {stats.get('by_category')}")
    print(f"risk       : {stats.get('aggregate_risk')}/10  coverage: {stats.get('coverage')}%")
    print(f"chains     : {[c['chain_id'] for c in stats.get('chains', [])]}")
    drift = stats.get("drift", {})
    for tid, row in (drift.get("per_target") or {}).items():
        print(f"drift {tid:11s} baseline_refusal={row['baseline']['refusal_rate']} "
              f"attack_refusal={row['attack']['refusal_rate']} "
              f"collapse={row['collapse_iteration']}")
    graph_row = db.query_one("SELECT graph FROM graphs WHERE run_id=?", (run_id,))
    graph = db.loads(graph_row["graph"], {}) if graph_row else {}
    print(f"graph      : {len(graph.get('nodes', []))} nodes / {len(graph.get('edges', []))} edges")
    reports = db.query("SELECT format, path FROM reports WHERE run_id=?", (run_id,))
    for rep in reports:
        print(f"report     : {rep['format']:4s} -> {rep['path']}")
    top = db.query("SELECT severity, title, target_id FROM findings WHERE run_id=? "
                   "ORDER BY severity DESC LIMIT 6", (run_id,))
    print("\ntop findings:")
    for f in top:
        print(f"  {f['severity']:.1f}  [{f['target_id']}] {f['title']}")


if __name__ == "__main__":
    main()
