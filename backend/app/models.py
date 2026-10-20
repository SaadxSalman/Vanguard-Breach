"""Pydantic request/response models for the Vanguard-Breach API."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SeverityLabel = Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
RunStatus = Literal["pending", "running", "completed", "failed", "cancelled"]


class CampaignIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    domain: str = "general"
    target_ids: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=lambda: [
        "scout", "planner", "injector", "inversion", "poisoner", "mcp", "chain"])
    config: dict[str, Any] = Field(default_factory=dict)


class CampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    domain: str | None = None
    target_ids: list[str] | None = None
    agents: list[str] | None = None
    config: dict[str, Any] | None = None


class LaunchOptions(BaseModel):
    seed: int | None = None
    max_iterations: int | None = None
    severity_threshold: float | None = None


class IngestDoc(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    category: str = "custom"
    source: str = "manual"
    meta: dict[str, Any] = Field(default_factory=dict)


class SearchQuery(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=50)
    collection: str = "threats"


class ProbeRequest(BaseModel):
    target_id: str
    message: str
    user_id: str = "redteam@vanguard.local"
    tenant: str = "tenant_a"


class FindingOut(BaseModel):
    id: str
    run_id: str
    campaign_id: str
    title: str
    category: str
    severity: float
    severity_label: str
    owasp: str
    atlas: str
    target_id: str
    description: str
    evidence: dict[str, Any]
    remediation: str
    chain_id: str
    status: str
    created_at: float
