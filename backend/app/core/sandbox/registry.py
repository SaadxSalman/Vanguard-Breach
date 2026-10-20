"""Sandbox target registry + remote (dockerized) target adapter."""
from __future__ import annotations

from typing import Any

import httpx

from ...config import get_settings
from .agent_targets import MCPGatewayTarget, OpsPilotTarget
from .base import SandboxTarget
from .rag_targets import FinGuardTarget, MediAssistTarget
from .vector_targets import KnowSphereTarget


def build_targets() -> dict[str, SandboxTarget]:
    targets: list[SandboxTarget] = [MediAssistTarget(), FinGuardTarget(),
                                    OpsPilotTarget(), KnowSphereTarget(), MCPGatewayTarget()]
    return {t.id: t for t in targets}


_TARGETS: dict[str, SandboxTarget] | None = None


def get_targets() -> dict[str, SandboxTarget]:
    global _TARGETS
    if _TARGETS is None:
        _TARGETS = build_targets()
    return _TARGETS


class RemoteTarget(SandboxTarget):
    """Adapter for a dockerized sandbox target fleet (VANGUARD_SANDBOX_MODE=remote)."""

    def __init__(self, target_id: str) -> None:
        super().__init__()
        self.id = target_id
        self._base = get_settings().target_base_url.rstrip("/")

    def chat(self, message: str, user_id: str = "redteam@vanguard.local",
             tenant: str = "tenant_a") -> Any:
        with httpx.Client(timeout=30) as client:
            resp = client.post(f"{self._base}/chat", json={
                "target_id": self.id, "message": message, "user_id": user_id, "tenant": tenant})
            resp.raise_for_status()
        from .base import ChatResponse
        data = resp.json()
        return ChatResponse(text=data.get("text", ""), refused=data.get("refused", False),
                            complied=data.get("complied", False),
                            retrieved=data.get("retrieved", []),
                            tool_calls=data.get("tool_calls", []),
                            meta=data.get("meta", {}))


def get_target(target_id: str) -> SandboxTarget:
    settings = get_settings()
    if settings.sandbox_mode == "remote":
        return RemoteTarget(target_id)
    targets = get_targets()
    if target_id not in targets:
        raise KeyError(f"unknown target '{target_id}'")
    return targets[target_id]
