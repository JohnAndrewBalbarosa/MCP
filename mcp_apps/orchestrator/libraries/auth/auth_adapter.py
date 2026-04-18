from __future__ import annotations

from mcp_apps.orchestrator.libraries.types.contracts import SessionProfile
from mcp_clients.agent_executor.client.mcp_router import llm_build_planner_session_profile


def bootstrap_planner_session() -> SessionProfile:
    # Planner auth now lives in the server-owned LLM gateway.
    return llm_build_planner_session_profile()
