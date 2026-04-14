from __future__ import annotations

from dataclasses import dataclass

from mcp_apps.orchestrator.libraries.config.env_loader import load_layered_env
from mcp_apps.orchestrator.libraries.types.contracts import ProviderConfig


@dataclass
class ResearchProviderSelection:
    provider_id: str
    config: ProviderConfig


def select_research_provider() -> ResearchProviderSelection:
    env = load_layered_env()
    provider_id = env.get("RESEARCH_PROVIDER", "default")
    api_url = env.get("RESEARCH_API_URL", "")
    if not api_url:
        raise ValueError("Set RESEARCH_API_URL")
    return ResearchProviderSelection(
        provider_id=provider_id,
        config=ProviderConfig(provider_id=provider_id, api_url=api_url),
    )
