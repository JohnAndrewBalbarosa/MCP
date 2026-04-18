from __future__ import annotations

from typing import Dict, List

from mcp_apps.orchestrator.libraries.types.contracts import SessionProfile
from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntimeView
from mcp_servers.llm_server.server.agents.modules.offline_fallback import (
    offline_fallback_enabled,
    offline_response,
)
from mcp_servers.llm_server.server.agents.modules.runtime_loader import load_runtime
from mcp_servers.llm_server.server.agents.vendors.registry import (
    get_batch_generator,
    get_provider_generator,
)
from mcp_servers.llm_server.server.trace_logger import log_generation


def describe_runtime(role: str) -> ProviderRuntimeView:
    return load_runtime(role).public_view()


def build_planner_session_profile() -> SessionProfile:
    runtime = load_runtime("PLANNER")
    headers: Dict[str, str] = {}
    if runtime.api_key:
        headers["Authorization"] = f"Bearer {runtime.api_key}"
    return SessionProfile(headers=headers, cookie_jar={})


def _safe_generate(role: str, prompt: str) -> str:
    runtime = load_runtime(role)
    provider_generate = get_provider_generator(runtime.provider_id)
    role_name = role.lower()

    try:
        response = provider_generate(runtime, prompt)
        log_generation(role_name, runtime.provider_id, runtime.model, prompt, response)
        return response
    except Exception as exc:
        if not offline_fallback_enabled():
            raise
        response = offline_response(role_name, prompt)
        log_generation(
            role_name,
            runtime.provider_id,
            runtime.model,
            prompt,
            response,
            transport="MOCK-FALLBACK",
            response_status="FALLBACK",
            error_message=str(exc),
        )
        return response


def generate_text(role: str, prompt: str) -> str:
    return _safe_generate(role, prompt)


def generate_texts(role: str, prompts: List[str]) -> List[str]:
    runtime = load_runtime(role)
    batch_generate = get_batch_generator(runtime.provider_id)

    if batch_generate is None:
        return [_safe_generate(role, prompt) for prompt in prompts]

    try:
        responses = batch_generate(runtime, prompts)
        for index, (prompt, response) in enumerate(zip(prompts, responses), start=1):
            log_generation(
                role.lower(),
                runtime.provider_id,
                runtime.model,
                prompt,
                response,
                prompt_index=index,
            )
        return responses
    except Exception as exc:
        if not offline_fallback_enabled():
            raise

        responses: List[str] = []
        for index, prompt in enumerate(prompts, start=1):
            response = offline_response(role.lower(), prompt)
            log_generation(
                role.lower(),
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


def get_context_limit(role: str) -> int:
    return load_runtime(role).max_context_lines
