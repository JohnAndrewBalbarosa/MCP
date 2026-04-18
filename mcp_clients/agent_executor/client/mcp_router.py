from __future__ import annotations

from mcp_apps.orchestrator.libraries.types.contracts import SessionProfile
from mcp_clients.agent_executor.libraries.types.contracts import ProviderRuntimeView
from mcp_shared.config.env_loader import load_env
from mcp_servers.filesystem_server.server.index import apply_snippet, get_snippet
from mcp_servers.llm_server.server.handlers.llm_handler import (
    handle_build_planner_session_profile,
    handle_describe_runtime,
    handle_generate_text,
    handle_generate_texts,
)


def _local_endpoint(endpoint: str) -> bool:
    return endpoint.startswith("http://127.0.0.1") or endpoint.startswith("http://localhost")


def _filesystem_endpoint() -> str:
    env = load_env()
    return env.get("FILESYSTEM_MCP_URL", "http://127.0.0.1:8101")


def _llm_endpoint() -> str:
    env = load_env()
    return env.get("LLM_MCP_URL", "http://127.0.0.1:8103")


def filesystem_get(file_path: str, start_line: int, end_line: int) -> str:
    endpoint = _filesystem_endpoint()
    if _local_endpoint(endpoint):
        return get_snippet(file_path=file_path, start_line=start_line, end_line=end_line)
    raise NotImplementedError("Remote MCP routing is not yet implemented in this scaffold")


def filesystem_apply(file_path: str, start_line: int, end_line: int, replacement: str) -> dict:
    endpoint = _filesystem_endpoint()
    if _local_endpoint(endpoint):
        return apply_snippet(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            replacement=replacement,
        )
    raise NotImplementedError("Remote MCP routing is not yet implemented in this scaffold")


def llm_describe_runtime(role: str) -> ProviderRuntimeView:
    endpoint = _llm_endpoint()
    if _local_endpoint(endpoint):
        runtime = handle_describe_runtime(role)
        return ProviderRuntimeView(
            provider_id=runtime.provider_id,
            model=runtime.model,
            max_output_tokens=runtime.max_output_tokens,
            temperature=runtime.temperature,
            top_p=runtime.top_p,
            max_parallel_instances=runtime.max_parallel_instances,
            max_context_lines=runtime.max_context_lines,
        )
    raise NotImplementedError("Remote MCP routing is not yet implemented in this scaffold")


def llm_build_planner_session_profile() -> SessionProfile:
    endpoint = _llm_endpoint()
    if _local_endpoint(endpoint):
        return handle_build_planner_session_profile()
    raise NotImplementedError("Remote MCP routing is not yet implemented in this scaffold")


def llm_generate_text(role: str, prompt: str) -> str:
    endpoint = _llm_endpoint()
    if _local_endpoint(endpoint):
        return handle_generate_text(role, prompt)
    raise NotImplementedError("Remote MCP routing is not yet implemented in this scaffold")


def llm_generate_texts(role: str, prompts: list[str]) -> list[str]:
    endpoint = _llm_endpoint()
    if _local_endpoint(endpoint):
        return handle_generate_texts(role, prompts)
    raise NotImplementedError("Remote MCP routing is not yet implemented in this scaffold")
