from __future__ import annotations

from typing import Any, Dict, List


def extract_function_headers(source_text: str, language_hint: str = "") -> List[Dict[str, str]]:
    """Extract compact function headers from source text or precomputed summaries."""
    del language_hint
    lines = [line.strip() for line in source_text.splitlines() if line.strip()]
    headers: List[Dict[str, str]] = []
    current: Dict[str, str] | None = None

    for line in lines:
        lowered = line.lower()
        if lowered.startswith("function:"):
            if current:
                headers.append(current)
            current = {
                "name": line.split(":", 1)[1].strip(),
                "description": "",
                "input": "",
                "output": "",
            }
            continue
        if current is None:
            continue
        if lowered.startswith("description:"):
            current["description"] = line.split(":", 1)[1].strip()
        elif lowered.startswith("input:"):
            current["input"] = line.split(":", 1)[1].strip()
        elif lowered.startswith("output:"):
            current["output"] = line.split(":", 1)[1].strip()

    if current:
        headers.append(current)
    return headers


def build_ground_truth_packet(compact_context: Dict[str, Any], artifact_snapshot: str = "") -> Dict[str, Any]:
    function_headers = compact_context.get("function_headers", [])
    branch_summary = str(compact_context.get("branch_summary", "")).strip()
    target_file = str(compact_context.get("artifact_path", "")).strip()
    constraints = compact_context.get("known_constraints", [])
    inputs = compact_context.get("known_inputs", [])
    outputs = compact_context.get("known_outputs", [])

    lines: List[str] = []
    if target_file:
        lines.append(f"file: {target_file}")
    if branch_summary:
        lines.append(f"summary: {branch_summary}")
    if constraints:
        lines.append(f"constraints: {', '.join(str(item) for item in constraints)}")
    if inputs:
        lines.append(f"inputs: {', '.join(str(item) for item in inputs)}")
    if outputs:
        lines.append(f"outputs: {', '.join(str(item) for item in outputs)}")

    for header in function_headers:
        lines.extend(
            [
                f"function: {header.get('name', '')}",
                f"description: {header.get('description', '') or 'No description'}",
                f"input: {header.get('input', '') or 'unknown'}",
                f"output: {header.get('output', '') or 'unknown'}",
            ]
        )

    if artifact_snapshot:
        lines.append(f"snapshot: {artifact_snapshot}")

    compact_context["next_agent_ground_truth"] = "\n".join(lines).strip()
    return compact_context


def should_reset_agent(node_metadata: Dict[str, Any]) -> bool:
    return bool(
        node_metadata.get("requires_fresh_agent")
        or node_metadata.get("merge_role") == "merge"
        or node_metadata.get("incoming_flow_count", 0) > 1
    )


def compact_branch_context(
    node_id: str,
    target_file: str,
    branch_outputs: List[str],
    *,
    artifact_summary: Dict[str, Any] | None = None,
    node_metadata: Dict[str, Any] | None = None,
    artifact_snapshot: str = "",
) -> Dict[str, Any]:
    summary = artifact_summary or {}
    function_headers = list(summary.get("function_headers", []))
    if not function_headers:
        function_headers = extract_function_headers("\n".join(branch_outputs))

    known_inputs = list(summary.get("known_inputs", []))
    known_outputs = list(summary.get("known_outputs", []))
    known_constraints = list(summary.get("known_constraints", []))
    branch_summary = str(summary.get("branch_summary") or "").strip()
    if not branch_summary:
        branch_summary = " | ".join(item.strip() for item in branch_outputs if item.strip())

    compact_context: Dict[str, Any] = {
        "node_id": node_id,
        "artifact_path": target_file,
        "branch_summary": branch_summary,
        "function_headers": function_headers,
        "known_constraints": known_constraints,
        "known_inputs": known_inputs,
        "known_outputs": known_outputs,
        "requires_fresh_agent": should_reset_agent(node_metadata or {}),
    }
    return build_ground_truth_packet(compact_context, artifact_snapshot=artifact_snapshot)
