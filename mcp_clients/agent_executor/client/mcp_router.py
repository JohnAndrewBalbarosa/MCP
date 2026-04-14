from __future__ import annotations

from mcp_clients.agent_executor.libraries.config.env_loader import load_layered_env
from mcp_servers.filesystem_server.server.index import apply_snippet, get_snippet


def _filesystem_endpoint() -> str:
    env = load_layered_env()
    endpoint = env.get("FILESYSTEM_MCP_URL")
    if not endpoint:
        raise ValueError("FILESYSTEM_MCP_URL is required in layered .env configuration")
    return endpoint


def filesystem_get(file_path: str, start_line: int, end_line: int) -> str:
    endpoint = _filesystem_endpoint()
    if endpoint.startswith("http://127.0.0.1") or endpoint.startswith("http://localhost"):
        return get_snippet(file_path=file_path, start_line=start_line, end_line=end_line)
    raise NotImplementedError("Remote MCP routing is not yet implemented in this scaffold")


def filesystem_apply(file_path: str, start_line: int, end_line: int, replacement: str) -> dict:
    endpoint = _filesystem_endpoint()
    if endpoint.startswith("http://127.0.0.1") or endpoint.startswith("http://localhost"):
        return apply_snippet(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            replacement=replacement,
        )
    raise NotImplementedError("Remote MCP routing is not yet implemented in this scaffold")
