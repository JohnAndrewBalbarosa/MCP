from __future__ import annotations

from mcp_apps.orchestrator.libraries.auth.session_store import save_session_profile
from mcp_apps.orchestrator.libraries.config.env_loader import load_layered_env
from mcp_apps.orchestrator.libraries.types.contracts import SessionProfile


def bootstrap_session() -> SessionProfile:
    """Phase 0 placeholder for Playwright login interception and profile capture."""
    env = load_layered_env()
    api_url = env.get("PLANNER_API_URL")
    if not api_url:
        raise ValueError("PLANNER_API_URL is required")

    profile = SessionProfile(
        base_url=api_url,
        headers={"Authorization": "Bearer <captured-token>"},
        cookie_jar={"session": "<captured-cookie>"},
    )
    save_session_profile(profile)
    return profile
