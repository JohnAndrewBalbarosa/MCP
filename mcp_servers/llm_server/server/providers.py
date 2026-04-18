from __future__ import annotations

from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntime
from mcp_servers.llm_server.server.agents.vendors.registry import (
    get_batch_generator,
    get_provider_generator,
)


def generate_completion(runtime: ProviderRuntime, prompt: str) -> str:
    provider_generate = get_provider_generator(runtime.provider_id)
    return provider_generate(runtime, prompt)


def generate_qwen_texts(runtime: ProviderRuntime, prompts: list[str]) -> list[str]:
    batch_generate = get_batch_generator(runtime.provider_id)
    if batch_generate is None:
        return [generate_completion(runtime, prompt) for prompt in prompts]
    return batch_generate(runtime, prompts)