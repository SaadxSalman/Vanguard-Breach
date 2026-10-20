"""Severity math and aggregate risk scoring."""
from __future__ import annotations

from typing import Any


def severity_label(value: float) -> str:
    if value >= 9.0:
        return "CRITICAL"
    if value >= 7.0:
        return "HIGH"
    if value >= 5.0:
        return "MEDIUM"
    if value >= 3.0:
        return "LOW"
    return "INFO"


def aggregate_risk(findings: list[dict[str, Any]]) -> float:
    """1 - Π(1 - sev/10): chained exposure compounded across findings (0..10)."""
    if not findings:
        return 0.0
    complement = 1.0
    for f in findings:
        complement *= (1.0 - min(10.0, float(f.get("severity", 0))) / 10.0)
    return round((1.0 - complement) * 10.0, 2)


def coverage_score(attempts: list[dict[str, Any]]) -> float:
    """% of (target × objective) pairs that were probed at least once."""
    if not attempts:
        return 0.0
    pairs = {(a.get("target_id"), a.get("objective")) for a in attempts}
    targets = {a.get("target_id") for a in attempts}
    objectives = {a.get("objective") for a in attempts}
    full = max(1, len(targets) * len(objectives))
    return round(100.0 * len(pairs) / full, 1)
