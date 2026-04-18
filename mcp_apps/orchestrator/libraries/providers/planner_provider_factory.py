from __future__ import annotations

from mcp_clients.agent_executor.client.mcp_router import llm_describe_runtime
from mcp_clients.agent_executor.libraries.types.contracts import ProviderRuntimeView


def select_planner_provider() -> ProviderRuntimeView:
    return llm_describe_runtime("PLANNER")
