from __future__ import annotations

from mcp_clients.agent_executor.client.mcp_router import (
    filesystem_apply,
    filesystem_get,
    llm_describe_runtime,
    llm_generate_text,
)
from mcp_clients.agent_executor.client.prompt_bounds import enforce_bounds
from mcp_clients.agent_executor.tools.response_parser import (
    render_compact_summary,
    strip_code_fences,
    summarize_generated_code,
)


def _build_executor_prompt(
    snippet: str,
    intent: str,
    target_file: str,
    abstraction_context: list[str],
    enforce_layered_design: bool,
) -> str:
    """Build a bounded code-mutation prompt for the executor LLM (Qwen).

    The agent receives only the exact snippet it is allowed to touch —
    no surrounding context, no other files.  It must return the replacement
    code only; no prose, no markdown fences.
    """
    new_file_note = (
        "\nThis is a NEW file — generate the complete file content from scratch."
        if not snippet.strip()
        else ""
    )

    architecture_policy = (
        "Use layered design implicitly unless the user request explicitly opts out.\n"
        "Keep abstractions separated by level (entrypoint, service logic, adapters).\n"
        "For new files, include concise section headers where language supports comments.\n"
        if enforce_layered_design
        else "Layered design is optional for this run.\n"
    )

    context_block = "\n".join(f"- {item}" for item in abstraction_context) or "- none"

    return (
        "You are an expert code mutation agent.\n"
        "You will receive a bounded code snippet and a mutation intent.\n"
        "Return ONLY the replacement code — no explanations, no markdown fences, "
        "no leading/trailing blank lines beyond what the snippet requires.\n\n"
        "Architectural policy:\n"
        f"{architecture_policy}\n"
        "Known abstractions from previous nodes:\n"
        f"{context_block}\n\n"
        f"File:             {target_file}{new_file_note}\n"
        f"Mutation intent:  {intent}\n\n"
        "Current snippet:\n"
        f"{snippet}\n\n"
        "Replacement code:"
    )


def execute_node(
    agent_id: str,
    graph,
    node_id: str,
    abstraction_context: list[str] | None = None,
    enforce_layered_design: bool = True,
) -> dict:
    """Execute one bounded DAG node using an ephemeral Qwen agent.

    Flow:
      1. Fetch the bounded snippet from the Filesystem MCP server.
         (Returns empty string for new files — executor generates full content.)
      2. Build a minimal executor prompt (snippet + mutation intent only).
    3. Call the executor LLM via the client MCP router.
      4. Strip markdown fences from the LLM response.
      5. Write the replacement back through the Filesystem MCP server.
    """
    node = graph.node_by_id[node_id]
    summaries = abstraction_context or []
    selection = llm_describe_runtime("EXECUTOR")
    payload = {
        "target_file": node.target_file,
        "start_line": node.start_line,
        "end_line": node.end_line,
        "mutation_intent": node.mutation_intent,
    }
    enforce_bounds(payload, max_span_lines=selection.max_context_lines)

    try:
        # Step 1: fetch only the bounded region — agent sees nothing else
        snippet = filesystem_get(node.target_file, node.start_line, node.end_line)

        # Step 2 + 3: build prompt and call Qwen executor
        prompt = _build_executor_prompt(
            snippet,
            node.mutation_intent,
            node.target_file,
            summaries,
            enforce_layered_design,
        )
        raw_replacement = llm_generate_text("EXECUTOR", prompt)

        # Step 4: strip any markdown fences the LLM wrapped around the code
        replacement = strip_code_fences(raw_replacement)

        summary_payload = summarize_generated_code(
            target_file=node.target_file,
            mutation_intent=node.mutation_intent,
            replacement=replacement,
        )

        # Step 5: deterministic splice back through MCP server
        write_result = filesystem_apply(
            node.target_file,
            node.start_line,
            node.end_line,
            replacement,
        )
        return {
            "ok": True,
            "agent_id": agent_id,
            "node_id": node_id,
            "status": "DONE",
            "summary": write_result.get("message", "applied"),
            "artifact_summary": summary_payload,
            "artifact_summary_text": render_compact_summary(summary_payload),
        }
    except Exception as exc:
        return {"ok": False, "agent_id": agent_id, "node_id": node_id, "error": str(exc)}
