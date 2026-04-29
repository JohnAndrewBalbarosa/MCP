from __future__ import annotations

from typing import Callable, Dict, List

from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntime
from mcp_servers.llm_server.server.agents.modules.defaults import Provider
from mcp_servers.llm_server.server.agents.vendors.gemini_agent import (
    generate_text as generate_gemini_text,
)
from mcp_servers.llm_server.server.agents.vendors.mock_agent import (
    generate_text as generate_mock_text,
)
from mcp_servers.llm_server.server.agents.vendors.mock_agent import (
    generate_texts as generate_mock_texts,
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
    if provider == Provider.MOCK:
        return generate_mock_text
    if provider in Provider._OPENAI_ALTS:
        return generate_openai_text
    if provider == Provider.GEMINI:
        return generate_gemini_text
    if provider in Provider._QWEN_ALTS:
        return generate_qwen_text
    raise ValueError(
        f"Unsupported provider_id: {provider_id!r}. "
        f"Valid options: mock, openai, open-ai, gemini, qwen, hugging-face, huggingface"
    )


def get_batch_generator(provider_id: str) -> ProviderBatchGenerator | None:
    provider = provider_id.lower()
    if provider == Provider.MOCK:
        return generate_mock_texts
    if provider in Provider._QWEN_ALTS:
        return generate_qwen_texts
    return None
