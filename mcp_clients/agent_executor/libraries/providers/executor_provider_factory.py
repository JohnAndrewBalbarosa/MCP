from __future__ import annotations

from dataclasses import dataclass

from mcp_clients.agent_executor.libraries.config.env_loader import load_layered_env


@dataclass
class ExecutorProviderSelection:
    provider_id: str
    api_url: str


def select_executor_provider() -> ExecutorProviderSelection:
    env = load_layered_env()
    provider_id = env.get("EXECUTOR_PROVIDER", "default")
    api_url = env.get("EXECUTOR_API_URL", "")
    if not api_url:
        raise ValueError("Set EXECUTOR_API_URL")
    return ExecutorProviderSelection(provider_id=provider_id, api_url=api_url)
