from __future__ import annotations

from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntimeView
from mcp_servers.llm_server.server.index import describe_planner_runtime


def select_planner_provider() -> ProviderRuntimeView:
    return describe_planner_runtime()
