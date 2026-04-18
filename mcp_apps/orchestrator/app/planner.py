from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from mcp_clients.agent_executor.client.mcp_router import llm_generate_text
from mcp_apps.orchestrator.libraries.types.contracts import DagGraph, DagNode, ResearchBrief


@dataclass
class Planner:
    """Builds a deterministic DAG with strict line-bounded mutation nodes."""

    def _workspace_tree_from_paths(self, paths: List[str]) -> dict[str, dict]:
        tree: dict[str, dict] = {}
        for relative_path in paths:
            parts = Path(relative_path).parts
            if not parts:
                continue
            cursor = tree
            for part in parts[:-1]:
                cursor = cursor.setdefault(part, {})
            cursor.setdefault("__files__", [])
            if parts[-1] not in cursor["__files__"]:
                cursor["__files__"].append(parts[-1])
        return tree

    def describe_workspace_context(self, workspace_context: Dict[str, Any] | None) -> str:
        if not workspace_context:
            return "workspace_root: unavailable"

        files = workspace_context.get("files", [])
        file_paths = [
            str(item.get("path", "")).strip()
            for item in files
            if str(item.get("path", "")).strip()
        ]
        tree = self._workspace_tree_from_paths(file_paths)

        lines = [f"workspace_root: {workspace_context.get('root', '')}"]
        lines.append(f"file_count: {workspace_context.get('file_count', len(file_paths))}")
        if workspace_context.get("truncated"):
            lines.append("note: workspace scan truncated")

        lines.append("tree:")
        lines.extend(self._render_workspace_tree(tree, indent=2))

        lines.append("file_previews:")
        for file_info in files:
            relative_path = str(file_info.get("path", "")).strip()
            preview = str(file_info.get("preview", "")).strip()
            if not relative_path:
                continue
            lines.append(f"- {relative_path}")
            if preview:
                for line in preview.splitlines():
                    lines.append(f"  {line}")
            else:
                lines.append("  (empty or unreadable)")

        return "\n".join(lines)

    def _describe_research_brief(self, research_brief: ResearchBrief) -> str:
        lines = [f"objective: {research_brief.objective}"]
        if research_brief.project_type:
            lines.append(f"project_type: {research_brief.project_type}")
        lines.append("constraints:")
        for item in research_brief.constraints:
            lines.append(f"- {item}")
        lines.append("assumptions:")
        for item in research_brief.assumptions:
            lines.append(f"- {item}")
        lines.append("risks:")
        for item in research_brief.risks:
            lines.append(f"- {item}")
        if research_brief.recommended_structure:
            lines.append("recommended_structure:")
            for item in research_brief.recommended_structure:
                lines.append(f"- {item}")
        return "\n".join(lines)

    def build_planner_prompt(
        self,
        request: str,
        research_brief: ResearchBrief,
        workspace_context: Dict[str, Any] | None = None,
    ) -> str:
        if research_brief.tech_stack:
            lifecycle_block = (
                f"  tech_stack: {research_brief.tech_stack}\n"
                f"  setup_commands: {research_brief.setup_commands}\n"
                f"  run_commands: {research_brief.run_commands}\n"
                f"  test_commands: {research_brief.test_commands}\n"
            )
        else:
            lifecycle_block = "  (tech stack unknown — infer from request)\n"

        workspace_block = self.describe_workspace_context(workspace_context)

        return (
            "You are the planner for a model-context-protocol coding orchestrator.\n"
            "Return STRICT JSON only — no prose, no markdown fences — "
            "with exactly these keys:\n"
            "  graph_id, created_at, nodes, command_nodes\n\n"
            "The Planner must generate a deterministic DAG from the "
            "research brief and workspace scan.\n"
            "=== WORKSPACE CONTEXT (scan of the launch directory) ===\n"
            f"{workspace_block}\n\n"
            "=== AGENT NODES (key: 'nodes') ===\n"
            "Each agent node = ONE file to create or edit. Use REAL file paths for the project.\n"
            "NEVER use placeholder names like 'example_service', "
            "'svc_a', 'svc_b', or 'handler.py'.\n"
            "Derive paths from the user request and tech stack.\n"
            "Good examples: 'src/index.js', 'backend/app.py', 'components/Login.jsx',\n"
            "  'public/index.html', 'routes/auth.js', 'models/user.py', 'styles/main.css'\n"
            "Required fields per agent node:\n"
            "  node_id              - short label: A, B, C, D...\n"
            "  status               - 'READY' if depends_on=[], else 'BLOCKED'\n"
            "  depends_on           - list of node_ids that must finish first\n"
            "  next                 - list of node_ids that follow this one\n"
            "  target_file          - REAL relative path matching the project structure\n"
            "  start_line           - 1 for a new file; realistic offset for partial edits\n"
            "  end_line             - estimated end line (e.g. 80 for a medium new file)\n"
            "  mutation_intent      - specific description "
            "of what to write/change in this file\n"
            "  acceptance_checks    - [] or list of validation commands\n"
            "  branch_key           - parallel group label "
            "('setup', 'frontend', 'backend', etc.)\n"
            "  outgoing_flow_count  - len(next)\n"
            "  incoming_flow_count  - len(depends_on)\n"
            "  task_type            - always 'agent'\n"
            "  terminal_command     - always ''\n\n"
            "=== COMMAND NODES (key: 'command_nodes') ===\n"
            "One command node per terminal command. "
            "ONLY use commands listed in the lifecycle block\n"
            "below — absolutely never invent commands, git operations, or publish steps.\n"
            "Command nodes run SEQUENTIALLY and ALL must complete "
            "before any agent node starts.\n"
            "Required fields: node_id (CMD-01, CMD-02...), status ('READY' or 'BLOCKED'),\n"
            "  depends_on, next, task_type='command', terminal_command (exact shell command),\n"
            "  command_scope ('repo' or 'workspace'), mutation_intent, acceptance_checks=[],\n"
            "  branch_key='command-flow', target_file='', start_line=0, end_line=0,\n"
            "  outgoing_flow_count, incoming_flow_count\n\n"
            "=== DAG RULES ===\n"
            "- No cycles.\n"
            "- Nodes sharing the same depends_on parent run "
            "IN PARALLEL (different branch_keys).\n"
            "- status='READY' only when depends_on is empty, otherwise 'BLOCKED'.\n"
            "- NEVER add git, pytest, pip, or any command not in the research brief.\n\n"
            "Return a single JSON object only. "
            "No comments, no markdown, no explanatory text.\n"
            "Use empty arrays for missing lists.\n"
            "Example shape: {\"graph_id\":\"...\","
            "\"created_at\":\"...\",\"nodes\":[...],"
            "\"command_nodes\":[...]}\n\n"
            f"User request:\n{request}\n\n"
            f"Research brief:\n{self._describe_research_brief(research_brief)}\n\n"
            "Lifecycle commands from Research Agent "
            f"(command_nodes source — use ONLY these):\n{lifecycle_block}"
        )

    def _planner_repair_prompt(
        self,
        request: str,
        research_brief: ResearchBrief,
        workspace_context: Dict[str, Any] | None,
        response_text: str,
    ) -> str:
        workspace_block = self.describe_workspace_context(workspace_context)
        return (
            "Rewrite the previous planner output as valid JSON only.\n"
            "The JSON must contain exactly these keys: graph_id, "
            "created_at, nodes, command_nodes.\n"
            "Every node in nodes and command_nodes must include: "
            "node_id, status, depends_on, next, target_file, "
            "start_line, end_line, mutation_intent, acceptance_checks, "
            "branch_key, outgoing_flow_count, incoming_flow_count, "
            "task_type, terminal_command, command_scope.\n"
            "Use empty arrays where appropriate. Do not add markdown fences or commentary.\n"
            "User request:\n"
            f"{request}\n\n"
            "Research brief:\n"
            f"{self._describe_research_brief(research_brief)}\n\n"
            "Workspace context:\n"
            f"{workspace_block}\n\n"
            "Invalid response to repair:\n"
            f"{response_text}\n"
        )

    def _extract_json_object(self, text: str) -> dict | None:
        """Multi-pass extraction: strip fences, find outermost balanced { }."""
        if not text or not text.strip():
            return None

        # Strip markdown code fences wherever they appear
        cleaned = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        cleaned = re.sub(r"```", "", cleaned).strip()

        start = cleaned.find("{")
        if start == -1:
            return None

        depth = 0
        end = -1
        for idx in range(start, len(cleaned)):
            if cleaned[idx] == "{":
                depth += 1
            elif cleaned[idx] == "}":
                depth -= 1
                if depth == 0:
                    end = idx
                    break

        if end == -1:
            return None

        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None

    def _graph_from_response(self, response: str) -> DagGraph | None:
        payload = self._extract_json_object(response)
        if payload is None:
            return None

        try:
            graph = DagGraph.from_dict(payload)
        except Exception:
            return None

        if not graph.nodes:
            return None

        return self._finalize_graph(graph)

    def _is_valid_graph(self, graph: DagGraph) -> bool:
        if not graph.nodes:
            return False
        node_ids = [node.node_id for node in graph.nodes]
        if len(node_ids) != len(set(node_ids)):
            return False
        for node in graph.nodes + graph.command_nodes:
            if not node.node_id:
                return False
            if not node.status:
                return False
            if node.depends_on is None or node.next is None:
                return False
        return True

    def _finalize_graph(self, graph: DagGraph) -> DagGraph:
        graph.normalize_flow_counts()
        return graph

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
            target_descriptor = (
                node.terminal_command
                if node.task_type == "command" and node.terminal_command
                else f"workspace/{node.target_file}:{node.start_line}-{node.end_line}"
                if node.target_file
                else "command"
            )
            lines.extend(
                [
                    f"- {node.node_id} [{node.status}] depends_on={depends_on} "
                    f"next={next_nodes} branch={node.branch_key} "
                    f"fan_out={node.outgoing_flow_count} "
                    f"fan_in={node.incoming_flow_count} type={node.task_type}",
                    f"  source_path={target_descriptor}",
                    f"  command={node.mutation_intent}",
                    f"  checks={checks}",
                ]
            )
            if node.task_type == "command" and node.terminal_command:
                lines.append(f"  terminal_command={node.terminal_command}")

        if graph.command_nodes:
            lines.append("Command Nodes:")
            for node in graph.command_nodes:
                depends_on = ", ".join(node.depends_on) if node.depends_on else "none"
                next_nodes = ", ".join(node.next) if node.next else "none"
                lines.extend(
                    [
                        f"- {node.node_id} [{node.status}] depends_on={depends_on} "
                        f"next={next_nodes} scope={node.command_scope}",
                        f"  command={node.terminal_command}",
                    ]
                )
        return "\n".join(lines)

    def describe_source_targets(self, graph: DagGraph) -> str:
        lines = ["Source Targets:"]
        for node in graph.nodes:
            if node.task_type == "command" and node.terminal_command:
                lines.append(f"- {node.node_id}: command -> {node.terminal_command}")
            elif node.target_file:
                lines.append(f"- {node.node_id}: workspace/{node.target_file}")
            else:
                lines.append(f"- {node.node_id}: command")
        return "\n".join(lines)

    def describe_workspace_structure(self, graph: DagGraph) -> str:
        tree: dict[str, dict] = {}
        for node in graph.nodes:
            if not node.target_file:
                continue
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
        research_brief: ResearchBrief | None = None,
    ) -> str:
        if research_brief is not None:
            unique_commands = self._collect_terminal_commands(research_brief)
        else:
            # Fallback: read from command_nodes already on graph
            unique_commands = [
                node.terminal_command
                for node in graph.command_nodes
                if node.terminal_command
            ]

        lines = [f"command_mode={command_mode}"]
        for index, command in enumerate(unique_commands, start=1):
            lines.append(f"{index}. {command}")
        return "\n".join(lines)

    def render_mermaid(self, graph: DagGraph) -> str:
        lines = ["flowchart TD"]
        for node in graph.command_nodes:
            if node.terminal_command:
                descriptor = node.terminal_command
            else:
                descriptor = node.mutation_intent
            label = (
                f"{node.node_id}\\n{descriptor}"
                f"\\nout={node.outgoing_flow_count} "
                f"in={node.incoming_flow_count}\\n{node.command_scope}"
            )
            label = label.replace('"', "'")
            lines.append(f'    {node.node_id}["{label}"]')
        for node in graph.nodes:
            if node.task_type == "command" and node.terminal_command:
                descriptor = node.terminal_command
            elif node.target_file:
                descriptor = (
                    f"{node.target_file}:"
                    f"{node.start_line}-{node.end_line}"
                )
            else:
                descriptor = node.mutation_intent

            label = (
                f"{node.node_id}\\n{descriptor}"
                f"\\nout={node.outgoing_flow_count} in={node.incoming_flow_count}"
            )
            if node.task_type != "agent":
                label += f"\\n{node.task_type}"
            label = label.replace('"', "'")
            lines.append(f'    {node.node_id}["{label}"]')
        for node in graph.command_nodes:
            for next_id in node.next:
                if next_id:
                    lines.append(f"    {node.node_id} --> {next_id}")
        for node in graph.nodes:
            for next_id in node.next:
                lines.append(f"    {node.node_id} --> {next_id}")
        return "\n".join(lines)

    def plan(
        self,
        request: str,
        research_brief: ResearchBrief,
        workspace_context: Dict[str, Any] | None = None,
    ) -> DagGraph:
        prompt = self.build_planner_prompt(
            request,
            research_brief,
            workspace_context=workspace_context,
        )
        last_response = ""

        for _attempt in range(2):
            response = llm_generate_text("PLANNER", prompt)
            last_response = response
            graph = self._graph_from_response(response)
            if graph is not None and self._is_valid_graph(graph):
                if not graph.command_nodes:
                    graph.command_nodes = self._build_command_nodes(
                        self._collect_terminal_commands(research_brief)
                    )
                return self._finalize_graph(graph)

            prompt = self._planner_repair_prompt(
                request,
                research_brief,
                workspace_context,
                response,
            )

        raise RuntimeError(
            "Planner did not return valid JSON after retries. "
            f"Last response: {last_response}"
        )

    def plan_parallel_coding_assistant(
        self,
        request: str,
        research_brief: ResearchBrief,
        workspace_context: Dict[str, Any] | None = None,
    ) -> DagGraph:
        return self.plan(request, research_brief, workspace_context=workspace_context)
