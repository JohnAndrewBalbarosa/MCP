from __future__ import annotations

from typing import Dict
import os

from mcp_apps.orchestrator.libraries.types.contracts import SessionProfile
from mcp_servers.llm_server.libraries.config.env_loader import load_layered_env
from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntime, ProviderRuntimeView
from mcp_servers.llm_server.server.providers import generate_completion, generate_qwen_texts
from mcp_servers.llm_server.server.trace_logger import log_generation


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


def _default_model(provider_id: str, role: str) -> str:
    if provider_id == "gemini":
        return "gemini-2.5-flash"
    if provider_id in {"open-ai", "openai"}:
        return "gpt-4.1-mini"
    if provider_id in {"hugging-face", "huggingface", "qwen"}:
        return "Qwen/Qwen2.5-Coder-7B-Instruct"
    if role == "RESEARCH":
        return "gemini-2.5-flash"
    if role == "PLANNER":
        return "gpt-4.1-mini"
    return "Qwen/Qwen2.5-Coder-7B-Instruct"


def _default_provider(role: str) -> str:
    if role == "RESEARCH":
        return "gemini"
    if role == "PLANNER":
        return "open-ai"
    return "qwen"


def _provider_requires_key(provider_id: str) -> bool:
    return provider_id.lower() in {"gemini", "open-ai", "openai", "hugging-face", "huggingface", "qwen"}


def _offline_fallback_enabled() -> bool:
    return os.environ.get("MCP_ALLOW_OFFLINE_FALLBACK", "0").strip().lower() in {"1", "true", "yes", "on"}


def _offline_response(role: str, prompt: str) -> str:
    prompt_head = " ".join(prompt.strip().split())[:160]
    if role == "research":
        return (
            "Offline research brief: keep generated code in the sandbox workspace, "
            "separate model/API logs by role, and export source targets plus command lists. "
            f"Prompt head: {prompt_head}"
        )
    if role == "planner":
        return (
            "Offline planner response: emit source targets, workspace structure, terminal commands, "
            "and planner artifacts for the archive. "
            f"Prompt head: {prompt_head}"
        )
    return (
        "Offline executor response: preserve bounded edits and comment-safe mutation text. "
        f"Prompt head: {prompt_head}"
    )


def _generate_text(role: str, runtime: ProviderRuntime, prompt: str) -> str:
    try:
        response = generate_completion(runtime, prompt)
        log_generation(role, runtime.provider_id, runtime.model, prompt, response)
        return response
    except Exception as exc:
        if not _offline_fallback_enabled():
            raise
        response = _offline_response(role, prompt)
        log_generation(
            role,
            runtime.provider_id,
            runtime.model,
            prompt,
            response,
            transport="MOCK-FALLBACK",
            response_status="FALLBACK",
            error_message=str(exc),
        )
        return response


def _load_runtime(role: str) -> ProviderRuntime:
    env = load_layered_env()
    prefix = role.upper()
    provider_id = env.get(f"{prefix}_PROVIDER", _default_provider(role))
    model = env.get(f"{prefix}_MODEL", _default_model(provider_id.lower(), role))
    api_key = env.get(f"{prefix}_API_KEY", "")
    max_output_tokens = _int_env(env, f"{prefix}_MAX_OUTPUT_TOKENS", 1024)
    temperature = _float_env(env, f"{prefix}_TEMPERATURE", 0.2)
    top_p = _float_env(env, f"{prefix}_TOP_P", 0.95)
    max_parallel_instances = _int_env(env, f"{prefix}_MAX_PARALLEL_INSTANCES", 4)
    max_context_lines = _int_env(env, f"{prefix}_MAX_CONTEXT_LINES", 16)
    if _provider_requires_key(provider_id) and not api_key:
        raise ValueError(f"Set {prefix}_API_KEY in mcp_servers/.env")
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


def describe_research_runtime() -> ProviderRuntimeView:
    return _load_runtime("RESEARCH").public_view()


def describe_planner_runtime() -> ProviderRuntimeView:
    return _load_runtime("PLANNER").public_view()


def describe_executor_runtime() -> ProviderRuntimeView:
    return _load_runtime("EXECUTOR").public_view()


def build_planner_session_profile() -> SessionProfile:
    runtime = _load_runtime("PLANNER")
    headers: Dict[str, str] = {}
    if runtime.api_key:
        headers["Authorization"] = f"Bearer {runtime.api_key}"
    return SessionProfile(headers=headers, cookie_jar={})


def generate_research_text(prompt: str) -> str:
    runtime = _load_runtime("RESEARCH")
    return _generate_text("research", runtime, prompt)


def generate_planner_text(prompt: str) -> str:
    runtime = _load_runtime("PLANNER")
    return _generate_text("planner", runtime, prompt)


def generate_executor_text(prompt: str) -> str:
    runtime = _load_runtime("EXECUTOR")
    return _generate_text("executor", runtime, prompt)


def generate_executor_texts(prompts: list[str]) -> list[str]:
    runtime = _load_runtime("EXECUTOR")
    if runtime.provider_id.lower() in {"hugging-face", "huggingface", "qwen"}:
        try:
            responses = generate_qwen_texts(runtime, prompts)
            for index, (prompt, response) in enumerate(zip(prompts, responses), start=1):
                log_generation(
                    "executor",
                    runtime.provider_id,
                    runtime.model,
                    prompt,
                    response,
                    prompt_index=index,
                )
            return responses
        except Exception as exc:
            if not _offline_fallback_enabled():
                raise
            responses = []
            for index, prompt in enumerate(prompts, start=1):
                response = _offline_response("executor", prompt)
                log_generation(
                    "executor",
                    runtime.provider_id,
                    runtime.model,
                    prompt,
                    response,
                    prompt_index=index,
                    transport="MOCK-FALLBACK",
                    response_status="FALLBACK",
                    error_message=str(exc),
                )
                responses.append(response)
            return responses
    responses = []
    for prompt in prompts:
        response = _generate_text("executor", runtime, prompt)
        responses.append(response)
    return responses


def get_executor_context_limit() -> int:
    return _load_runtime("EXECUTOR").max_context_lines