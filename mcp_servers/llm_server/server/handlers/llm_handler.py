from __future__ import annotations

from typing import List

from mcp_apps.orchestrator.libraries.types.contracts import SessionProfile
from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntimeView
from mcp_servers.llm_server.server.agents.entrypoint import (
    build_planner_session_profile,
    describe_runtime,
    generate_text,
    generate_texts,
    get_context_limit,
)


def handle_describe_runtime(role: str) -> ProviderRuntimeView:
    return describe_runtime(role)


def handle_build_planner_session_profile() -> SessionProfile:
    return build_planner_session_profile()


def handle_generate_text(role: str, prompt: str) -> str:
    return generate_text(role, prompt)


def handle_generate_texts(role: str, prompts: List[str]) -> List[str]:
    return generate_texts(role, prompts)


def handle_context_limit(role: str) -> int:
    return get_context_limit(role)
