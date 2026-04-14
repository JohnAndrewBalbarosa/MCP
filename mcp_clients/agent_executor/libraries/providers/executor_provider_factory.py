from __future__ import annotations

from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntimeView
from mcp_servers.llm_server.server.index import describe_executor_runtime


def select_executor_provider() -> ProviderRuntimeView:
    return describe_executor_runtime()
