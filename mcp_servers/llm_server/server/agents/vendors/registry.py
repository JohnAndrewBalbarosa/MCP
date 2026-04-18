from __future__ import annotations

from typing import Callable, Dict, List

from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntime
from mcp_servers.llm_server.server.agents.vendors.gemini_agent import (
    generate_text as generate_gemini_text,
)
from mcp_servers.llm_server.server.agents.vendors.openai_agent import (
    generate_text as generate_openai_text,
)
from mcp_servers.llm_server.server.agents.vendors.qwen_agent import (
    generate_text as generate_qwen_text,
)
from mcp_servers.llm_server.server.agents.vendors.qwen_agent import (
    generate_texts as generate_qwen_texts,
)

ProviderGenerator = Callable[[ProviderRuntime, str], str]
ProviderBatchGenerator = Callable[[ProviderRuntime, List[str]], List[str]]


def get_provider_generator(provider_id: str) -> ProviderGenerator:
    provider = provider_id.lower()
    if provider in {"open-ai", "openai"}:
        return generate_openai_text
    if provider == "gemini":
        return generate_gemini_text
    if provider in {"hugging-face", "huggingface", "qwen"}:
        return generate_qwen_text
    raise ValueError(f"Unsupported provider_id: {provider_id}")


def get_batch_generator(provider_id: str) -> ProviderBatchGenerator | None:
    provider = provider_id.lower()
    if provider in {"hugging-face", "huggingface", "qwen"}:
        return generate_qwen_texts
    return None
