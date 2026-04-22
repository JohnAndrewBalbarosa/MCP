from __future__ import annotations

from mcp_apps.orchestrator.libraries.auth.session_store import save_session_profile
from mcp_apps.orchestrator.libraries.types.contracts import SessionProfile
from mcp_clients.agent_executor.client.mcp_router import llm_build_planner_session_profile


def bootstrap_session() -> SessionProfile:
    """Phase 0 placeholder for Playwright login interception and profile capture."""
    profile = SessionProfile(
        headers={"Authorization": "Bearer <captured-token>"},
        cookie_jar={"session": "<captured-cookie>"},
    )
    save_session_profile(profile)
    return profile


def bootstrap_planner_session() -> SessionProfile:
    """Fetch planner session profile from the server-owned LLM gateway."""
    return llm_build_planner_session_profile()
