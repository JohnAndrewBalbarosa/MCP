from __future__ import annotations

from mcp_apps.orchestrator.libraries.types.contracts import SessionProfile
from mcp_servers.llm_server.server.index import build_planner_session_profile


def bootstrap_planner_session() -> SessionProfile:
    # Planner auth now lives in the server-owned LLM gateway.
    return build_planner_session_profile()
