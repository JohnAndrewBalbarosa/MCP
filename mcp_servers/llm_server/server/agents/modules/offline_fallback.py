from __future__ import annotations

import os


def offline_fallback_enabled() -> bool:
    raw = os.environ.get("MCP_ALLOW_OFFLINE_FALLBACK", "0")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def offline_response(role: str, prompt: str) -> str:
    prompt_head = " ".join(prompt.strip().split())[:160]
    role_name = role.lower()

    if role_name == "research":
        return (
            "Offline research brief: keep generated code in sandbox workspace, "
            "separate model logs by role, and export command lists. "
            f"Prompt head: {prompt_head}"
        )

    if role_name == "planner":
        return (
            "Offline planner response: emit source targets, workspace structure, "
            "terminal commands, and planner artifacts. "
            f"Prompt head: {prompt_head}"
        )

    return (
        "Offline executor response: preserve bounded edits and comment-safe "
        f"mutation text. Prompt head: {prompt_head}"
    )
