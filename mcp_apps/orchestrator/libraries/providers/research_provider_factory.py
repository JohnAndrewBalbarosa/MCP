from __future__ import annotations

from typing import Literal

from mcp_clients.agent_executor.client.mcp_router import llm_describe_runtime
from mcp_clients.agent_executor.libraries.types.contracts import ProviderRuntimeView


ProviderRole = Literal["PLANNER", "RESEARCH"]


def select_provider(role: ProviderRole) -> ProviderRuntimeView:
    """Select a runtime configuration for a known orchestrator role."""
    normalized_role = role.strip().upper()
    if normalized_role not in {"PLANNER", "RESEARCH"}:
        raise ValueError(f"Unsupported provider role: {role}")
    return llm_describe_runtime(normalized_role)


def select_planner_provider() -> ProviderRuntimeView:
    return select_provider("PLANNER")


def select_research_provider() -> ProviderRuntimeView:
    return select_provider("RESEARCH")
