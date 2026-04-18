from __future__ import annotations

from mcp_apps.orchestrator.libraries.types.contracts import SessionProfile
from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntimeView
from mcp_servers.llm_server.server.handlers.llm_handler import (
    handle_build_planner_session_profile,
    handle_context_limit,
    handle_describe_runtime,
    handle_generate_text,
    handle_generate_texts,
)


def describe_research_runtime() -> ProviderRuntimeView:
    return handle_describe_runtime("RESEARCH")


def describe_planner_runtime() -> ProviderRuntimeView:
    return handle_describe_runtime("PLANNER")


def describe_executor_runtime() -> ProviderRuntimeView:
    return handle_describe_runtime("EXECUTOR")


def build_planner_session_profile() -> SessionProfile:
    return handle_build_planner_session_profile()


def generate_research_text(prompt: str) -> str:
    return handle_generate_text("RESEARCH", prompt)


def generate_planner_text(prompt: str) -> str:
    return handle_generate_text("PLANNER", prompt)


def generate_executor_text(prompt: str) -> str:
    return handle_generate_text("EXECUTOR", prompt)


def generate_executor_texts(prompts: list[str]) -> list[str]:
    return handle_generate_texts("EXECUTOR", prompts)


def get_executor_context_limit() -> int:
    return handle_context_limit("EXECUTOR")