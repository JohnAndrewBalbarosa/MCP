from __future__ import annotations

from typing import Dict

from mcp_shared.config.env_loader import load_env
from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntime
from mcp_servers.llm_server.server.agents.modules.defaults import (
    default_model,
    default_provider,
    provider_requires_key,
)


def _int_env(env: Dict[str, str], key: str, default: int) -> int:
    raw = env.get(key, str(default))
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{key} must be an integer") from exc


def _float_env(env: Dict[str, str], key: str, default: float) -> float:
    raw = env.get(key, str(default))
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{key} must be a number") from exc


def load_runtime(role: str) -> ProviderRuntime:
    env = load_env()
    prefix = role.upper()

    provider_id = env.get(f"{prefix}_PROVIDER", default_provider(prefix))
    model = env.get(f"{prefix}_MODEL", default_model(provider_id, prefix))
    api_key = env.get(f"{prefix}_API_KEY", "")

    max_output_tokens = _int_env(env, f"{prefix}_MAX_OUTPUT_TOKENS", 1024)
    temperature = _float_env(env, f"{prefix}_TEMPERATURE", 0.2)
    top_p = _float_env(env, f"{prefix}_TOP_P", 0.95)
    max_parallel_instances = _int_env(env, f"{prefix}_MAX_PARALLEL_INSTANCES", 4)
    max_context_lines = _int_env(env, f"{prefix}_MAX_CONTEXT_LINES", 16)

    if provider_requires_key(provider_id) and not api_key:
        raise ValueError(f"Set {prefix}_API_KEY in the repo root .env")

    return ProviderRuntime(
        provider_id=provider_id,
        model=model,
        api_key=api_key,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        top_p=top_p,
        max_parallel_instances=max_parallel_instances,
        max_context_lines=max_context_lines,
    )
