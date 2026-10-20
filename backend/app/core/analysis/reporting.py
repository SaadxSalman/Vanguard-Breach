"""Report generation: Markdown, standalone HTML (inline SVG graph) and JSON."""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from typing import Any

from ... import db
from ...config import get_settings


def _md_rows(findings: list[dict[str, Any]]) -> str:
    rows = []
    for f in sorted(findings, key=lambda x: -x.get("severity", 0)):
        rows.append(f"| {f.get('severity', 0):.1f} | {f.get('severity_label', '')} | "
                    f"{f.get('title', '')} | {f.get('owasp', '')} | {f.get('target_id', '')} |")
    return "\n".join(rows)


def _html_rows(findings: list[dict[str, Any]]) -> str:
    rows = []
    for f in sorted(findings, key=lambda x: -x.get("severity", 0)):
        rows.append("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in (
            f"{f.get('severity', 0):.1f}", f.get("severity_label", ""), f.get("title", ""),
            f.get("owasp", ""), f.get("target_id", ""))) + "</tr>")
    return "".join(rows)


def _svg_graph(graph: dict[str, Any]) -> str:
    """Minimal layered SVG rendering of the attack graph for the HTML report."""
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if not nodes:
        return "<p>No attack paths recorded.</p>"
    layers: dict[int, list[dict[str, Any]]] = {}
    for n in nodes:
        layers.setdefault(n.get("layer", 0), []).append(n)
    width = 1100
    height = 130 + 110 * max(len(v) for v in layers.values())
    max_layer = max(layers) or 1
    positions: dict[str, tuple[int, int]] = {}
    parts = [f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
             f'style="width:100%;height:auto;background:#0b0f17;border-radius:10px">']
    for layer, group in sorted(layers.items()):
        x = 90 + layer * ((width - 200) / max_layer)
        for i, node in enumerate(group):
            y = 70 + i * 110 + (55 if len(group) == 1 else 0)
            positions[node["id"]] = (x, y)
    for edge in edges:
        if edge["source"] in positions and edge["target"] in positions:
            x1, y1 = positions[edge["source"]]
            x2, y2 = positions[edge["target"]]
            color = "#ff4d6d" if edge.get("kind") == "boundary" else "#8be9fd"
            parts.append(f'<line x1="{x1 + 75}" y1="{y1}" x2="{x2 - 75}" y2="{y2}" '
                         f'stroke="{color}" stroke-width="1.6" stroke-dasharray="5,4"/>')
    for node_id, (x, y) in positions.items():
        node = next(n for n in nodes if n["id"] == node_id)
        fill = "#2b1216" if node.get("status") == "breached" else "#10201c"
        stroke = "#ff4d6d" if node.get("status") == "breached" else "#38d9a9"
        label = html.escape(node.get("label", node_id)[:34])
        parts.append(f'<rect x="{x - 75}" y="{y - 26}" width="150" height="52" rx="9" '
                     f'fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
        parts.append(f'<text x="{x}" y="{y + 4}" text-anchor="middle" fill="#e6edf3" '
                     f'font-size="11" font-family="monospace">{label}</text>')
    parts.append("</svg>")
    return "".join(parts)


def build_report(run: dict[str, Any], campaign: dict[str, Any], findings: list[dict[str, Any]],
                 graph: dict[str, Any], drift: dict[str, Any], stats: dict[str, Any],
                 summary: str) -> dict[str, Any]:
    settings = get_settings()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    target_ids = campaign.get("target_ids", [])
    if isinstance(target_ids, str):
        target_ids = json.loads(target_ids or "[]")
    md = [
        f"# Vanguard-Breach Red-Team Report — {campaign.get('name', '')}",
        "",
        f"**Client:** {settings.company_name}  ",
        f"**Run:** `{run.get('id')}`  |  **Campaign:** `{campaign.get('id')}`  |  "
        f"**Executed:** {now}  |  **Operator:** {settings.report_author}",
        "", "## Executive Summary", "", summary, "",
        "## Scope", "",
        f"- Domain playbook: **{campaign.get('domain', 'general')}**",
        f"- Targets: {', '.join(target_ids)}",
        f"- Payloads executed: **{stats.get('payloads_executed', 0)}**  |  "
        f"Findings: **{len(findings)}**  |  "
        f"Aggregate risk: **{stats.get('aggregate_risk', 0)}/10**",
        "", "## Findings", "",
        "| Sev | Level | Title | OWASP | Target |", "|---|---|---|---|---|",
        _md_rows(findings), "",
    ]
    for f in sorted(findings, key=lambda x: -x.get("severity", 0)):
        md += [f"### {f.get('severity', 0):.1f} — {f.get('title', '')}",
               f"- **Category:** {f.get('category')} | **{f.get('owasp')} / {f.get('atlas')}** | "
               f"Target: `{f.get('target_id')}`", f.get("description", ""), ""]
    if stats.get("chains"):
        md.append("## Validated Exploit Chains\n")
        for chain in stats["chains"]:
            md.append(f"### {chain['title']} (impact {chain['impact']:.1f})\n")
            for step in chain["steps"]:
                md.append(f"{step['step']}. {step['action']} _(finding `{step['finding']}`)_")
            md.append("")
    md += ["## Behavioral Drift", ""]
    for target_id, row in (drift.get("per_target", {}) or {}).items():
        md.append(f"- **{target_id}**: baseline refusal rate {row['baseline']['refusal_rate']} → "
                  f"attack {row['attack']['refusal_rate']} "
                  f"(collapse at iteration {row['collapse_iteration']})")
    md += ["", "## Remediation", ""]
    for item in stats.get("remediation", []):
        md += [f"### {item['title']}", item.get("markdown", ""), ""]
    markdown_text = "\n".join(md)

    html_doc = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Vanguard-Breach Report — {html.escape(campaign.get('name', ''))}</title>
<style>body{{background:#0b0f17;color:#e6edf3;font:14px/1.6 ui-monospace,Consolas,monospace;margin:0;padding:32px}}
h1{{color:#ff6b81}} h2{{color:#ff6b81}} h3{{color:#ffd166}} table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #233042;padding:6px 10px;font-size:12px}} code{{background:#161b26;padding:2px 5px;border-radius:4px}}
.card{{background:#101623;border:1px solid #233042;border-radius:12px;padding:18px;margin:14px 0}}</style></head><body>
<h1>⛨ Vanguard-Breach Red-Team Report</h1>
<div class="card"><b>{html.escape(campaign.get('name', ''))}</b> — {html.escape(settings.company_name)}<br>
Run <code>{html.escape(str(run.get('id')))}</code> · {now} · payloads: {stats.get('payloads_executed', 0)}
· findings: {len(findings)} · aggregate risk: {stats.get('aggregate_risk', 0)}/10</div>
<h2>Executive Summary</h2><div class="card">{html.escape(summary)}</div>
<h2>Attack Graph</h2><div class="card">{_svg_graph(graph)}</div>
<h2>Findings</h2><div class="card"><table><tr><th>Sev</th><th>Level</th><th>Title</th><th>OWASP</th><th>Target</th></tr>
{_html_rows(findings)}</table></div></body></html>"""

    payload = {"run": {"id": run.get("id"), "status": run.get("status")},
               "campaign": {"id": campaign.get("id"), "name": campaign.get("name"),
                            "domain": campaign.get("domain")},
               "generated_at": now, "summary": summary, "stats": stats,
               "findings": findings, "attack_graph": graph, "drift": drift}
    return {"markdown": markdown_text, "html": html_doc, "json": payload}


def persist_report(run_id: str, report: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    settings.report_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    for fmt, content in (("md", report["markdown"]), ("html", report["html"])):
        path = settings.report_dir / f"{run_id}.{fmt}"
        path.write_text(content, encoding="utf-8")
        db.insert("reports", {"id": db.new_id("rep"), "run_id": run_id, "format": fmt,
                              "path": str(path),
                              "summary": db.dumps({"bytes": len(content)}),
                              "created_at": db.now()})
        written[fmt] = str(path)
    json_path = settings.report_dir / f"{run_id}.json"
    json_path.write_text(json.dumps(report["json"], indent=2, default=str), encoding="utf-8")
    db.insert("reports", {"id": db.new_id("rep"), "run_id": run_id, "format": "json",
                          "path": str(json_path), "summary": "{}", "created_at": db.now()})
    written["json"] = str(json_path)
    return written
