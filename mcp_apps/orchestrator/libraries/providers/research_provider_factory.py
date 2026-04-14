from __future__ import annotations

from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntimeView
from mcp_servers.llm_server.server.index import describe_research_runtime


def select_research_provider() -> ProviderRuntimeView:
    return describe_research_runtime()
