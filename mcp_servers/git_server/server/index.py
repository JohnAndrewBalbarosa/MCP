from __future__ import annotations

import subprocess

from mcp_servers.git_server.libraries.config.env_loader import load_layered_env


def server_bind_url() -> str:
    env = load_layered_env()
    bind_url = env.get("GIT_SERVER_BIND_URL")
    if not bind_url:
        raise ValueError("GIT_SERVER_BIND_URL is required in layered .env configuration")
    return bind_url


def git_status(repo_path: str) -> str:
    result = subprocess.run(
        ["git", "-C", repo_path, "status", "--short"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()
