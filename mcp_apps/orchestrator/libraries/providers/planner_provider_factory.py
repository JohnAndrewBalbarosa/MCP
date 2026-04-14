from __future__ import annotations

from dataclasses import dataclass

from mcp_apps.orchestrator.libraries.config.env_loader import load_layered_env
from mcp_apps.orchestrator.libraries.types.contracts import ProviderConfig


@dataclass
class PlannerProviderSelection:
    provider_id: str
    config: ProviderConfig


def select_planner_provider() -> PlannerProviderSelection:
    env = load_layered_env()
    provider_id = env.get("PLANNER_PROVIDER", "default")
    api_url = env.get("PLANNER_API_URL", "")
    if not api_url:
        raise ValueError("Set PLANNER_API_URL")
    return PlannerProviderSelection(
        provider_id=provider_id,
        config=ProviderConfig(provider_id=provider_id, api_url=api_url),
    )
