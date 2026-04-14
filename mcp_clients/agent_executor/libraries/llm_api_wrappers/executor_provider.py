from __future__ import annotations

from mcp_clients.agent_executor.libraries.providers.executor_provider_factory import select_executor_provider
from mcp_servers.llm_server.server.index import generate_executor_text


def complete_mutation(prompt: str) -> str:
    selection = select_executor_provider()
    generated = generate_executor_text(prompt)
    return f"Executor({selection.provider_id}/{selection.model}) response for prompt length={len(prompt)}: {generated}"
