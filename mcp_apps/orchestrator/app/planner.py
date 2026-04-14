from __future__ import annotations

from dataclasses import dataclass
from typing import List

from mcp_apps.orchestrator.libraries.types.contracts import DagGraph, DagNode, ResearchBrief


@dataclass
class Planner:
    """Builds a deterministic DAG with strict line-bounded mutation nodes."""

    def describe_plan(self, graph: DagGraph) -> str:
        lines = [f"Graph: {graph.graph_id}"]
        for node in graph.nodes:
            depends_on = ", ".join(node.depends_on) if node.depends_on else "none"
            next_nodes = ", ".join(node.next) if node.next else "none"
            checks = "; ".join(node.acceptance_checks) if node.acceptance_checks else "none"
            lines.extend(
                [
                    f"- {node.node_id} [{node.status}] depends_on={depends_on} next={next_nodes}",
                    f"  target={node.target_file}:{node.start_line}-{node.end_line}",
                    f"  command={node.mutation_intent}",
                    f"  checks={checks}",
                ]
            )
        return "\n".join(lines)

    def render_mermaid(self, graph: DagGraph) -> str:
        lines = ["flowchart TD"]
        for node in graph.nodes:
            label = f"{node.node_id}\\n{node.target_file}:{node.start_line}-{node.end_line}"
            label = label.replace('"', "'")
            lines.append(f'    {node.node_id}["{label}"]')
        for node in graph.nodes:
            for next_id in node.next:
                lines.append(f"    {node.node_id} --> {next_id}")
        return "\n".join(lines)

    def plan(self, request: str, research_brief: ResearchBrief) -> DagGraph:
        nodes: List[DagNode] = [
            DagNode(
                node_id="A",
                status="READY",
                depends_on=[],
                next=["B"],
                target_file="example_service/main.py",
                start_line=10,
                end_line=20,
                mutation_intent=f"Request slice: {request}; research: {research_brief.objective}",
                acceptance_checks=["pytest tests/test_example.py::test_behavior"],
                branch_key="path-0",
            ),
            DagNode(
                node_id="B",
                status="BLOCKED",
                depends_on=["A"],
                next=["C", "D"],
                target_file="example_service/main.py",
                start_line=30,
                end_line=40,
                mutation_intent="Prepare branch fan-out",
                acceptance_checks=["pytest tests/test_example.py::test_branch"],
                branch_key="path-0",
            ),
            DagNode(
                node_id="C",
                status="BLOCKED",
                depends_on=["B"],
                next=[],
                target_file="svc_a/handler.py",
                start_line=65,
                end_line=76,
                mutation_intent="Branch C implementation",
                acceptance_checks=["pytest tests/test_svc_a.py::test_handler"],
                branch_key="path-1",
            ),
            DagNode(
                node_id="D",
                status="BLOCKED",
                depends_on=["B"],
                next=[],
                target_file="svc_b/handler.py",
                start_line=44,
                end_line=54,
                mutation_intent="Branch D implementation",
                acceptance_checks=["pytest tests/test_svc_b.py::test_handler"],
                branch_key="path-2",
            ),
        ]
        return DagGraph(graph_id="feature-001", nodes=nodes)
