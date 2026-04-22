from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class FlowNodeMeta:
    node_id: str
    incoming_edges: int
    outgoing_edges: int
    is_merge: bool
    is_branch: bool
    branch_width: int
    requires_new_executor: bool


def build_flow_index(graph) -> Dict[str, FlowNodeMeta]:
    flow_index: Dict[str, FlowNodeMeta] = {}

    for node in graph.nodes:
        incoming = node.incoming_flow_count or len(node.depends_on)
        outgoing = node.outgoing_flow_count or len(node.next)
        is_merge = incoming > 1
        is_branch = outgoing > 1

        branch_parent = False
        if incoming == 1:
            parent = graph.node_by_id[node.depends_on[0]]
            branch_parent = (parent.outgoing_flow_count or len(parent.next)) > 1

        requires_new_executor = bool(
            getattr(node, "requires_fresh_agent", False)
            or incoming == 0
            or is_merge
            or branch_parent
        )
        flow_index[node.node_id] = FlowNodeMeta(
            node_id=node.node_id,
            incoming_edges=incoming,
            outgoing_edges=outgoing,
            is_merge=is_merge,
            is_branch=is_branch,
            branch_width=outgoing if is_branch else 1,
            requires_new_executor=requires_new_executor,
        )

    return flow_index


def parallel_waves(graph) -> List[List[str]]:
    depth_cache: Dict[str, int] = {}

    def node_depth(node_id: str) -> int:
        cached = depth_cache.get(node_id)
        if cached is not None:
            return cached

        node = graph.node_by_id[node_id]
        if not node.depends_on:
            depth_cache[node_id] = 1
            return 1

        depth = 1 + max(node_depth(dep) for dep in node.depends_on)
        depth_cache[node_id] = depth
        return depth

    waves: Dict[int, List[str]] = {}
    for node in graph.nodes:
        waves.setdefault(node_depth(node.node_id), []).append(node.node_id)

    return [waves[level] for level in sorted(waves)]


def recommended_executor_count(graph) -> int:
    waves = parallel_waves(graph)
    if not waves:
        return 0
    return max(len(wave) for wave in waves)


def render_flow_report(graph) -> str:
    flow_index = build_flow_index(graph)
    waves = parallel_waves(graph)

    lines: List[str] = ["Flow Parser Report:"]
    lines.append(f"recommended_executor_pool={recommended_executor_count(graph)}")

    for idx, wave in enumerate(waves, start=1):
        lines.append(f"wave_{idx}: {', '.join(wave)}")

    lines.append("nodes:")
    for node in graph.nodes:
        meta = flow_index[node.node_id]
        lines.append(
            f"- {meta.node_id}: in={meta.incoming_edges} out={meta.outgoing_edges} "
            f"merge={meta.is_merge} branch={meta.is_branch} "
            f"new_executor={meta.requires_new_executor}"
        )

    return "\n".join(lines)
