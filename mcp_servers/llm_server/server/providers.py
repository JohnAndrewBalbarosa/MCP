from __future__ import annotations
from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntime

from mcp_servers.llm_server.server.gemini_provider import generate_text as generate_gemini_text
from mcp_servers.llm_server.server.openai_provider import generate_text as generate_openai_text
from mcp_servers.llm_server.server.qwen_provider import generate_text as generate_qwen_text
from mcp_servers.llm_server.server.qwen_provider import generate_texts as generate_qwen_texts


def generate_completion(runtime: ProviderRuntime, prompt: str) -> str:
    provider_id = runtime.provider_id.lower()
    if provider_id in {"open-ai", "openai"}:
        return generate_openai_text(runtime, prompt)
    if provider_id == "gemini":
        return generate_gemini_text(runtime, prompt)
    if provider_id in {"hugging-face", "huggingface", "qwen"}:
        return generate_qwen_text(runtime, prompt)
    raise ValueError(f"Unsupported provider_id: {runtime.provider_id}")