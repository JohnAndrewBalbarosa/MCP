from __future__ import annotations

from mcp_apps.orchestrator.libraries.auth.playwright_setup import bootstrap_session as bootstrap_playwright
from mcp_apps.orchestrator.libraries.config.env_loader import load_layered_env
from mcp_apps.orchestrator.libraries.providers.planner_provider_factory import select_planner_provider
from mcp_apps.orchestrator.libraries.types.contracts import SessionProfile


def bootstrap_planner_session() -> SessionProfile:
    env = load_layered_env()
    selection = select_planner_provider()
    auth_mode = env.get("PLANNER_AUTH_MODE", "api_key").lower()

    if auth_mode == "playwright":
        return bootstrap_playwright()

    # Generic fallback for API-key or token-based providers.
    return SessionProfile(base_url=selection.config.api_url, headers={}, cookie_jar={})
