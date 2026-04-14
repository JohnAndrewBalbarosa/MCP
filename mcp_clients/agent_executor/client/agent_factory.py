from __future__ import annotations

from mcp_clients.agent_executor.client.worker import execute_node


def run_ephemeral_agent(agent_id: str, graph, node_id: str) -> dict:
    """Runs one bounded node task and returns deterministic status."""
    return execute_node(agent_id=agent_id, graph=graph, node_id=node_id)
