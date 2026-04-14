from __future__ import annotations

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - handled at runtime if dependency is missing
    OpenAI = None

from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntime


def generate_text(runtime: ProviderRuntime, prompt: str) -> str:
    if OpenAI is None:
        raise RuntimeError("Install openai to enable the OpenAI provider backend")

    client = OpenAI(api_key=runtime.api_key)
    response = client.chat.completions.create(
        model=runtime.model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=runtime.max_output_tokens,
        temperature=runtime.temperature,
        top_p=runtime.top_p,
    )
    content = response.choices[0].message.content if response.choices else ""
    return (content or "").strip()