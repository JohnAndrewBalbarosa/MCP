from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict, Iterable, List

from mcp_apps.orchestrator.libraries.types.contracts import DagGraph, DagNode, ResearchBrief


def _coerce_graph(planning_payload: DagGraph | Dict[str, Any]) -> DagGraph:
    if isinstance(planning_payload, DagGraph):
        return planning_payload
    if not isinstance(planning_payload, dict):
        raise TypeError("planning_payload must be a DagGraph or dict")
    return DagGraph.from_dict(planning_payload)


def _ensure_edge_consistency(graph: DagGraph) -> None:
    """Keep depends_on and next in sync so later scheduling logic can trust adjacency."""
    node_map = graph.node_by_id

    cleaned_next: Dict[str, List[str]] = {}
    for node in graph.nodes + graph.command_nodes:
        seen: set[str] = set()
        cleaned: List[str] = []
        for next_id in node.next:
            if next_id not in node_map or next_id in seen:
                continue
            seen.add(next_id)
            cleaned.append(next_id)
        cleaned_next[node.node_id] = cleaned
        node.next = cleaned

    for node in graph.nodes + graph.command_nodes:
        node.depends_on = [dep for dep in node.depends_on if dep in node_map]

    for source_id, next_ids in cleaned_next.items():
        for next_id in next_ids:
            candidate = node_map[next_id]
            if source_id not in candidate.depends_on:
                candidate.depends_on.append(source_id)

    for node in graph.nodes + graph.command_nodes:
        rebuilt_next: List[str] = []
        for candidate in graph.nodes + graph.command_nodes:
            if node.node_id in candidate.depends_on and candidate.node_id not in rebuilt_next:
                rebuilt_next.append(candidate.node_id)
        node.next = rebuilt_next


def derive_prerequisites(
    candidate_nodes: Iterable[DagNode],
    workspace_context: Dict[str, Any] | None = None,
) -> Dict[str, List[str]]:
    del workspace_context
    return {node.node_id: list(node.depends_on) for node in candidate_nodes}


def _wave_levels(prerequisites: Dict[str, List[str]]) -> Dict[str, int]:
    depth_cache: Dict[str, int] = {}

    def node_depth(node_id: str) -> int:
        cached = depth_cache.get(node_id)
        if cached is not None:
            return cached

        deps = prerequisites.get(node_id, [])
        if not deps:
            depth_cache[node_id] = 1
            return 1

        depth = 1 + max(node_depth(dep) for dep in deps)
        depth_cache[node_id] = depth
        return depth

    for node_id in prerequisites:
        node_depth(node_id)
    return depth_cache


def classify_parallel_groups(
    candidate_nodes: Iterable[DagNode],
    prerequisites: Dict[str, List[str]],
) -> List[List[str]]:
    node_ids = [node.node_id for node in candidate_nodes]
    levels = _wave_levels({node_id: prerequisites.get(node_id, []) for node_id in node_ids})

    waves: Dict[int, List[str]] = defaultdict(list)
    for node_id in node_ids:
        waves[levels[node_id]].append(node_id)
    return [waves[level] for level in sorted(waves)]


def detect_merge_points(prerequisites: Dict[str, List[str]]) -> List[str]:
    return [node_id for node_id, deps in prerequisites.items() if len(deps) > 1]


def _parent_branching(node: DagNode, node_map: Dict[str, DagNode]) -> bool:
    if len(node.depends_on) != 1:
        return False
    parent = node_map.get(node.depends_on[0])
    return parent is not None and len(parent.next) > 1


def mark_agent_reset_boundaries(graph: DagGraph) -> DagGraph:
    node_map = graph.node_by_id

    for node in graph.nodes:
        is_merge = len(node.depends_on) > 1
        is_branch = len(node.next) > 1
        node.merge_role = "merge" if is_merge else "branch" if is_branch else "linear"
        node.requires_fresh_agent = (
            len(node.depends_on) == 0
            or is_merge
            or _parent_branching(node, node_map)
        )
        node.handoff_strategy = "ground_truth" if (is_merge or is_branch or node.requires_fresh_agent) else "reuse"

    for node in graph.command_nodes:
        node.merge_role = "command"
        node.requires_fresh_agent = True
        node.handoff_strategy = "command"

    return graph


def _annotate_parallel_groups(graph: DagGraph) -> None:
    prerequisites = derive_prerequisites(graph.nodes)
    levels = _wave_levels(prerequisites)
    for node in graph.nodes:
        node.parallel_group = f"wave-{levels[node.node_id]}"
    for node in graph.command_nodes:
        node.parallel_group = "command-flow"


def _normalize_statuses(graph: DagGraph) -> None:
    for node in graph.nodes:
        node.status = "READY" if not node.depends_on else "BLOCKED"
    for index, node in enumerate(graph.command_nodes):
        node.status = "READY" if index == 0 and not node.depends_on else "BLOCKED"


def _clamp_agent_bounds(graph: DagGraph, executor_max_span_lines: int) -> None:
    max_span = max(1, executor_max_span_lines)
    for node in graph.nodes:
        if node.task_type == "command":
            continue
        if node.start_line < 1:
            node.start_line = 1
        if node.end_line < node.start_line:
            node.end_line = node.start_line
        span = node.end_line - node.start_line + 1
        if span > max_span:
            node.end_line = node.start_line + max_span - 1


def render_header_summary(graph: DagGraph) -> str:
    lines: List[str] = []
    for node in graph.nodes:
        deps = ", ".join(node.depends_on) if node.depends_on else "none"
        lines.extend(
            [
                f"node: {node.node_id}",
                f"description: {node.mutation_intent or node.target_file or 'scheduled work item'}",
                f"input: {deps}",
                f"output: {node.target_file or 'workspace mutation'}",
                f"prerequisites: {deps}",
                f"parallel-group: {node.parallel_group or 'wave-unknown'}",
                f"fresh-agent: {'yes' if node.requires_fresh_agent else 'no'}",
            ]
        )
    return "\n".join(lines)


def build_dag(
    planning_payload: DagGraph | Dict[str, Any],
    workspace_context: Dict[str, Any] | None,
    research_brief: ResearchBrief,
    executor_max_span_lines: int = 16,
) -> DagGraph:
    del workspace_context
    del research_brief

    graph = _coerce_graph(planning_payload)
    _ensure_edge_consistency(graph)
    graph.normalize_flow_counts()
    _annotate_parallel_groups(graph)
    mark_agent_reset_boundaries(graph)
    _normalize_statuses(graph)
    _clamp_agent_bounds(graph, executor_max_span_lines)
    graph.normalize_flow_counts()
    return graph
