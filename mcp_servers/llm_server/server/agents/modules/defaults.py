from __future__ import annotations


class Provider:
    MOCK        = "mock"
    GEMINI      = "gemini"
    OPEN_AI     = "open-ai"
    OPENAI      = "openai"
    QWEN        = "qwen"
    HUGGING_FACE = "hugging-face"
    HUGGINGFACE  = "huggingface"

    _OPENAI_ALTS: frozenset[str] = frozenset({"open-ai", "openai"})
    _QWEN_ALTS:   frozenset[str] = frozenset({"hugging-face", "huggingface", "qwen"})
    _KEY_REQUIRED: frozenset[str] = frozenset({"gemini", "open-ai", "openai", "hugging-face", "huggingface", "qwen"})


def default_provider(role: str) -> str:
    role_name = role.upper()
    if role_name == "RESEARCH":
        return Provider.GEMINI
    if role_name == "PLANNER":
        return Provider.OPEN_AI
    return Provider.QWEN


def default_model(provider_id: str, role: str) -> str:
    provider = provider_id.lower()
    if provider == Provider.MOCK:
        return "mock-local-v1"
    if provider == Provider.GEMINI:
        return "gemini-2.5-flash"
    if provider in Provider._OPENAI_ALTS:
        return "gpt-4.1-mini"
    if provider in Provider._QWEN_ALTS:
        return "Qwen/Qwen2.5-Coder-7B-Instruct"

    role_name = role.upper()
    if role_name == "RESEARCH":
        return "gemini-2.5-flash"
    if role_name == "PLANNER":
        return "gpt-4.1-mini"
    return "Qwen/Qwen2.5-Coder-7B-Instruct"


def provider_requires_key(provider_id: str) -> bool:
    return provider_id.lower() in Provider._KEY_REQUIRED
