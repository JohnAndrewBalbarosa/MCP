from __future__ import annotations

from mcp_servers.filesystem_server.libraries.config.env_loader import load_layered_env
from mcp_servers.filesystem_server.server.file_mutator import apply_bounded_splice, read_bounded_snippet


def server_bind_url() -> str:
    env = load_layered_env()
    bind_url = env.get("FILESYSTEM_SERVER_BIND_URL")
    if not bind_url:
        raise ValueError("FILESYSTEM_SERVER_BIND_URL is required in layered .env configuration")
    return bind_url


def get_snippet(file_path: str, start_line: int, end_line: int) -> str:
    return read_bounded_snippet(file_path, start_line, end_line)


def apply_snippet(file_path: str, start_line: int, end_line: int, replacement: str) -> dict:
    apply_bounded_splice(file_path, start_line, end_line, replacement)
    return {
        "ok": True,
        "message": f"Applied bounded splice to {file_path}:{start_line}-{end_line}",
    }
