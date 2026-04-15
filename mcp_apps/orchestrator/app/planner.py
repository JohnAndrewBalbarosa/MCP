from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from mcp_apps.orchestrator.libraries.types.contracts import DagGraph, DagNode, ResearchBrief


@dataclass
class Planner:
    """Builds a deterministic DAG with strict line-bounded mutation nodes."""

    def describe_parallel_waves(self, graph: DagGraph) -> str:
        depth_cache: dict[str, int] = {}

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

        waves: dict[int, List[str]] = {}
        for node in graph.nodes:
            waves.setdefault(node_depth(node.node_id), []).append(node.node_id)

        lines = ["Parallel Waves:"]
        for wave_number in sorted(waves):
            lines.append(f"Wave {wave_number}: {', '.join(waves[wave_number])}")
        return "\n".join(lines)

    def describe_plan(self, graph: DagGraph) -> str:
        lines = [f"Graph: {graph.graph_id}"]
        for node in graph.nodes:
            depends_on = ", ".join(node.depends_on) if node.depends_on else "none"
            next_nodes = ", ".join(node.next) if node.next else "none"
            checks = "; ".join(node.acceptance_checks) if node.acceptance_checks else "none"
            lines.extend(
                [
                    f"- {node.node_id} [{node.status}] depends_on={depends_on} next={next_nodes}",
                    f"  source_path=workspace/{node.target_file}:{node.start_line}-{node.end_line}",
                    f"  command={node.mutation_intent}",
                    f"  checks={checks}",
                ]
            )
        return "\n".join(lines)

    def describe_source_targets(self, graph: DagGraph) -> str:
        lines = ["Source Targets:"]
        for node in graph.nodes:
            lines.append(f"- {node.node_id}: workspace/{node.target_file}")
        return "\n".join(lines)

    def describe_workspace_structure(self, graph: DagGraph) -> str:
        tree: dict[str, dict] = {}
        for node in graph.nodes:
            parts = Path(node.target_file).parts
            cursor = tree
            for part in parts[:-1]:
                cursor = cursor.setdefault(part, {})
            cursor.setdefault("__files__", [])
            if parts[-1] not in cursor["__files__"]:
                cursor["__files__"].append(parts[-1])

        lines = ["workspace/"]
        lines.extend(self._render_workspace_tree(tree, indent=2))
        return "\n".join(lines)

    def _render_workspace_tree(self, tree: dict[str, dict], indent: int) -> List[str]:
        lines: List[str] = []
        child_dirs = sorted(key for key in tree.keys() if key != "__files__")
        for directory in child_dirs:
            lines.append(f"{' ' * indent}{directory}/")
            lines.extend(self._render_workspace_tree(tree[directory], indent + 2))
        for filename in sorted(tree.get("__files__", [])):
            lines.append(f"{' ' * indent}{filename}")
        return lines

    def describe_terminal_commands(
        self,
        graph: DagGraph,
        command_mode: str = "batch",
        include_publish_commands: bool = False,
    ) -> str:
        commands: List[str] = []
        for node in graph.nodes:
            commands.extend(node.acceptance_checks)
        commands.append("python -m unittest discover -s tests -t .")
        if include_publish_commands:
            commands.extend(
                [
                    "git checkout -b feature/parallel-coding-assistant",
                    "git status",
                    "git add .",
                    'git commit -m "Implement parallel coding assistant tasks"',
                    "git push origin feature/parallel-coding-assistant",
                ]
            )

        unique_commands: List[str] = []
        for command in commands:
            if command not in unique_commands:
                unique_commands.append(command)

        lines = [f"command_mode={command_mode}"]
        for index, command in enumerate(unique_commands, start=1):
            lines.append(f"{index}. {command}")
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

    def plan_parallel_coding_assistant(self, request: str, research_brief: ResearchBrief) -> DagGraph:
        nodes: List[DagNode] = [
            DagNode(
                node_id="A",
                status="READY",
                depends_on=[],
                next=["B", "C", "D"],
                target_file="example_service/main.py",
                start_line=10,
                end_line=20,
                mutation_intent=(
                    f"Bootstrap the parallel coding assistant workspace for: {request}; "
                    f"research: {research_brief.objective}"
                ),
                acceptance_checks=["python -m unittest discover -s tests -t ."],
                branch_key="parallel-wave-0",
            ),
            DagNode(
                node_id="B",
                status="BLOCKED",
                depends_on=["A"],
                next=[],
                target_file="example_service/main.py",
                start_line=30,
                end_line=40,
                mutation_intent="Implement the main code path in parallel",
                acceptance_checks=["pytest tests/test_example.py::test_behavior"],
                branch_key="parallel-wave-1",
            ),
            DagNode(
                node_id="C",
                status="BLOCKED",
                depends_on=["A"],
                next=[],
                target_file="svc_a/handler.py",
                start_line=65,
                end_line=76,
                mutation_intent="Implement the first parallel branch",
                acceptance_checks=["pytest tests/test_svc_a.py::test_handler"],
                branch_key="parallel-wave-1",
            ),
            DagNode(
                node_id="D",
                status="BLOCKED",
                depends_on=["A"],
                next=[],
                target_file="svc_b/handler.py",
                start_line=44,
                end_line=54,
                mutation_intent="Implement the second parallel branch",
                acceptance_checks=["pytest tests/test_svc_b.py::test_handler"],
                branch_key="parallel-wave-1",
            ),
        ]
        return DagGraph(graph_id="parallel-coding-assistant", nodes=nodes)
