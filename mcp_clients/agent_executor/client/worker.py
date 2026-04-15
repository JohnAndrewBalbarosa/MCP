from __future__ import annotations

from mcp_clients.agent_executor.client.mcp_router import filesystem_apply, filesystem_get
from mcp_clients.agent_executor.client.prompt_bounds import enforce_bounds
from mcp_clients.agent_executor.libraries.providers.executor_provider_factory import select_executor_provider
from mcp_clients.agent_executor.libraries.llm_api_wrappers.executor_provider import complete_mutation


def _fake_mutation(snippet: str, intent: str) -> str:
    # Keep mutation behavior unchanged; provider call currently records selection metadata.
    complete_mutation(intent)
    return snippet


def execute_node(agent_id: str, graph, node_id: str) -> dict:
    node = graph.node_by_id[node_id]
    selection = select_executor_provider()
    payload = {
        "target_file": node.target_file,
        "start_line": node.start_line,
        "end_line": node.end_line,
        "mutation_intent": node.mutation_intent,
    }
    enforce_bounds(payload, max_span_lines=selection.max_context_lines)

    try:
        snippet = filesystem_get(node.target_file, node.start_line, node.end_line)
        replacement = _fake_mutation(snippet, node.mutation_intent)
        write_result = filesystem_apply(node.target_file, node.start_line, node.end_line, replacement)
        return {
            "ok": True,
            "agent_id": agent_id,
            "node_id": node_id,
            "status": "DONE",
            "summary": write_result.get("message", "applied"),
        }
    except Exception as exc:
        return {"ok": False, "agent_id": agent_id, "node_id": node_id, "error": str(exc)}
