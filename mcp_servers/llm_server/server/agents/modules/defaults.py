from __future__ import annotations


def default_provider(role: str) -> str:
    role_name = role.upper()
    if role_name == "RESEARCH":
        return "gemini"
    if role_name == "PLANNER":
        return "open-ai"
    return "qwen"


def default_model(provider_id: str, role: str) -> str:
    provider = provider_id.lower()
    if provider == "gemini":
        return "gemini-2.5-flash"
    if provider in {"open-ai", "openai"}:
        return "gpt-4.1-mini"
    if provider in {"hugging-face", "huggingface", "qwen"}:
        return "Qwen/Qwen2.5-Coder-7B-Instruct"

    role_name = role.upper()
    if role_name == "RESEARCH":
        return "gemini-2.5-flash"
    if role_name == "PLANNER":
        return "gpt-4.1-mini"
    return "Qwen/Qwen2.5-Coder-7B-Instruct"


def provider_requires_key(provider_id: str) -> bool:
    provider = provider_id.lower()
    return provider in {"gemini", "open-ai", "openai", "hugging-face", "huggingface", "qwen"}
