from __future__ import annotations

from mcp_apps.orchestrator.libraries.auth.session_store import save_session_profile
from mcp_apps.orchestrator.libraries.types.contracts import SessionProfile


def bootstrap_session() -> SessionProfile:
    """Phase 0 placeholder for Playwright login interception and profile capture."""
    profile = SessionProfile(
        headers={"Authorization": "Bearer <captured-token>"},
        cookie_jar={"session": "<captured-cookie>"},
    )
    save_session_profile(profile)
    return profile
