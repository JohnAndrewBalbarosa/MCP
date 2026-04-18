from __future__ import annotations

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover
    genai = None
    types = None

from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntime


def generate_text(runtime: ProviderRuntime, prompt: str) -> str:
    if genai is None or types is None:
        raise RuntimeError("Install google-genai to enable Gemini provider backend")

    config = types.GenerateContentConfig(
        max_output_tokens=runtime.max_output_tokens,
        temperature=runtime.temperature,
        top_p=runtime.top_p,
    )
    with genai.Client(api_key=runtime.api_key) as client:
        response = client.models.generate_content(
            model=runtime.model,
            contents=prompt,
            config=config,
        )
    return (response.text or "").strip()
