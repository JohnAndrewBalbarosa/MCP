from __future__ import annotations

from mcp_clients.agent_executor.libraries.providers.executor_provider_factory import select_executor_provider


def complete_mutation(prompt: str) -> str:
    selection = select_executor_provider()
    # Placeholder until per-provider adapters are added.
    return f"Executor({selection.provider_id}) response for prompt length={len(prompt)} via {selection.api_url}"
