"""Campaign CRUD + launch endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Response

from .. import db
from ..config import get_settings
from ..core.orchestrator import RUNNER
from ..models import CampaignIn, CampaignUpdate, LaunchOptions

router = APIRouter(prefix="/api")


def _campaign_row(campaign_id: str) -> dict[str, Any]:
    row = db.query_one("SELECT * FROM campaigns WHERE id=?", (campaign_id,))
    if not row:
        raise HTTPException(404, "campaign not found")
    return row


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    row = dict(row)
    row["target_ids"] = db.loads(row.get("target_ids"), [])
    row["agents"] = db.loads(row.get("agents"), [])
    row["config"] = db.loads(row.get("config"), {})
    return row


@router.get("/campaigns")
def list_campaigns() -> list[dict[str, Any]]:
    rows = db.query("SELECT * FROM campaigns ORDER BY created_at DESC")
    out = []
    for row in rows:
        item = _serialize(row)
        runs = db.query("SELECT id, status, created_at, progress FROM runs "
                        "WHERE campaign_id=? ORDER BY created_at DESC LIMIT 1", (row["id"],))
        item["latest_run"] = runs[0] if runs else None
        out.append(item)
    return out


@router.post("/campaigns", status_code=201)
def create_campaign(body: CampaignIn) -> dict[str, Any]:
    campaign_id = db.new_id("cmp")
    ts = db.now()
    db.insert("campaigns", {"id": campaign_id, "name": body.name,
                            "description": body.description, "domain": body.domain,
                            "target_ids": db.dumps(body.target_ids),
                            "agents": db.dumps(body.agents),
                            "config": db.dumps(body.config), "status": "draft",
                            "created_at": ts, "updated_at": ts})
    return _serialize(_campaign_row(campaign_id))


@router.get("/campaigns/{campaign_id}")
def get_campaign(campaign_id: str) -> dict[str, Any]:
    item = _serialize(_campaign_row(campaign_id))
    item["runs"] = db.query("SELECT * FROM runs WHERE campaign_id=? ORDER BY created_at DESC",
                            (campaign_id,))
    for run in item["runs"]:
        run["stats"] = db.loads(run.get("stats"), {})
    return item


@router.put("/campaigns/{campaign_id}")
def update_campaign(campaign_id: str, body: CampaignUpdate) -> dict[str, Any]:
    _campaign_row(campaign_id)
    fields: dict[str, Any] = {}
    if body.name is not None:
        fields["name"] = body.name
    if body.description is not None:
        fields["description"] = body.description
    if body.domain is not None:
        fields["domain"] = body.domain
    if body.target_ids is not None:
        fields["target_ids"] = db.dumps(body.target_ids)
    if body.agents is not None:
        fields["agents"] = db.dumps(body.agents)
    if body.config is not None:
        fields["config"] = db.dumps(body.config)
    fields["updated_at"] = db.now()
    sets = ", ".join(f"{k}=?" for k in fields)
    db.execute(f"UPDATE campaigns SET {sets} WHERE id=?", (*fields.values(), campaign_id))
    return _serialize(_campaign_row(campaign_id))


@router.delete("/campaigns/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: str) -> Response:
    _campaign_row(campaign_id)
    db.execute("DELETE FROM campaigns WHERE id=?", (campaign_id,))
    return Response(status_code=204)


@router.post("/campaigns/{campaign_id}/launch", status_code=202)
def launch_campaign(campaign_id: str, body: LaunchOptions | None = None) -> dict[str, Any]:
    campaign = _campaign_row(campaign_id)
    run_id = db.new_id("run")
    db.insert("runs", {"id": run_id, "campaign_id": campaign_id, "status": "pending",
                       "seed": (body.seed if body else None) or get_settings().default_seed,
                       "created_at": db.now()})
    db.execute("UPDATE campaigns SET status='running', updated_at=? WHERE id=?",
               (db.now(), campaign_id))
    RUNNER.launch(run_id, campaign, body.model_dump() if body else {})
    return {"run_id": run_id, "campaign_id": campaign_id, "status": "pending"}


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    run = db.query_one("SELECT * FROM runs WHERE id=?", (run_id,))
    if not run:
        raise HTTPException(404, "run not found")
    run["stats"] = db.loads(run.get("stats"), {})
    graph_row = db.query_one("SELECT graph FROM graphs WHERE run_id=?", (run_id,))
    run["has_graph"] = bool(graph_row)
    run["findings_count"] = db.query_one(
        "SELECT COUNT(*) AS n FROM findings WHERE run_id=?", (run_id,))["n"]
    return run


@router.get("/runs/{run_id}/events")
def run_events(run_id: str, since_id: int = 0) -> list[dict[str, Any]]:
    rows = db.query("SELECT * FROM events WHERE run_id=? AND id>? ORDER BY id LIMIT 500",
                    (run_id, since_id))
    for row in rows:
        row["data"] = db.loads(row.get("data"), {})
    return rows


@router.get("/runs/{run_id}/attack-graph")
def run_attack_graph(run_id: str) -> dict[str, Any]:
    row = db.query_one("SELECT graph FROM graphs WHERE run_id=?", (run_id,))
    if not row:
        raise HTTPException(404, "attack graph not generated yet")
    return db.loads(row["graph"], {})


@router.get("/findings")
def list_findings(run_id: str | None = None, campaign_id: str | None = None,
                  min_severity: float = 0.0) -> list[dict[str, Any]]:
    sql = "SELECT * FROM findings WHERE severity>=?"
    params: list[Any] = [min_severity]
    if run_id:
        sql += " AND run_id=?"
        params.append(run_id)
    if campaign_id:
        sql += " AND campaign_id=?"
        params.append(campaign_id)
    sql += " ORDER BY severity DESC"
    out = db.query(sql, tuple(params))
    for row in out:
        row["evidence"] = db.loads(row.get("evidence"), {})
    return out


@router.get("/reports/{run_id}")
def get_report(run_id: str, format: str = "md"):
    from fastapi import Response
    settings = get_settings()
    path = settings.report_dir / f"{run_id}.{format}"
    if not path.exists():
        raise HTTPException(404, f"report ({format}) not generated yet")
    media = {"md": "text/markdown", "html": "text/html",
             "json": "application/json"}.get(format, "text/plain")
    return Response(content=path.read_text(encoding="utf-8"), media_type=media)
