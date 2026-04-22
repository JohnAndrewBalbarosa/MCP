from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from mcp_clients.agent_executor.client.mcp_router import (
    llm_describe_runtime,
    llm_generate_text,
)
from mcp_apps.orchestrator.app.dag_builder import build_dag
from mcp_apps.orchestrator.libraries.types.contracts import DagGraph, DagNode, ResearchBrief


PLANNER_PROMPT_TEMPLATE = (
    Path(__file__).resolve().parent / "prompts" / "planner_prompt.txt"
)


@dataclass
class Planner:
    """Builds a deterministic DAG with strict line-bounded mutation nodes."""

    def _render_planner_prompt_template(
        self,
        request: str,
        research_brief: ResearchBrief,
        workspace_block: str,
        lifecycle_block: str,
    ) -> str:
        try:
            template = PLANNER_PROMPT_TEMPLATE.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Planner prompt template missing: {PLANNER_PROMPT_TEMPLATE}"
            ) from exc

        return (
            template.replace("__WORKSPACE_BLOCK__", workspace_block)
            .replace("__USER_REQUEST__", request)
            .replace("__RESEARCH_BRIEF__", self._describe_research_brief(research_brief))
            .replace("__LIFECYCLE_BLOCK__", lifecycle_block)
        )

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

        cwd_entries = workspace_context.get("cwd_entries", [])
        files = workspace_context.get("files", [])
        file_paths = [
            str(item.get("path", "")).strip()
            for item in files
            if str(item.get("path", "")).strip()
        ]
        tree = self._workspace_tree_from_paths(file_paths)

        lines = [f"workspace_root: {workspace_context.get('root', '')}"]
        if cwd_entries:
            lines.append("cwd_entries:")
            for item in cwd_entries:
                lines.append(f"- {item}")
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
        return self._render_planner_prompt_template(
            request=request,
            research_brief=research_brief,
            workspace_block=workspace_block,
            lifecycle_block=lifecycle_block,
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

    def _graph_from_response(
        self,
        response: str,
        research_brief: ResearchBrief,
        workspace_context: Dict[str, Any] | None,
    ) -> DagGraph | None:
        payload = self._extract_json_object(response)
        if payload is None:
            return None

        try:
            graph = build_dag(
                payload,
                workspace_context=workspace_context,
                research_brief=research_brief,
                executor_max_span_lines=self._executor_max_context_lines(),
            )
        except Exception:
            return None

        if not graph.nodes:
            return None

        return graph

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

    def _executor_max_context_lines(self) -> int:
        try:
            runtime = llm_describe_runtime("EXECUTOR")
            return max(1, int(runtime.max_context_lines))
        except Exception:
            return 16

    def _normalize_agent_bounds(self, graph: DagGraph) -> None:
        max_span = self._executor_max_context_lines()
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

    def _workspace_known_paths(self, workspace_context: Dict[str, Any] | None) -> set[str]:
        if not workspace_context:
            return set()

        known: set[str] = set()
        for entry in workspace_context.get("cwd_entries", []):
            item = str(entry).strip().rstrip("/").lower()
            if item:
                known.add(item)

        for file_info in workspace_context.get("files", []):
            raw = str(file_info.get("path", "")).strip().strip("/")
            if not raw:
                continue
            lowered = raw.lower()
            known.add(lowered)
            parts = [part for part in lowered.split("/") if part]
            for index in range(1, len(parts)):
                known.add("/".join(parts[:index]))

        return known

    def _looks_like_next_workspace(self, workspace_context: Dict[str, Any] | None) -> bool:
        known = self._workspace_known_paths(workspace_context)
        if not known:
            return False

        required_any = {
            "app/page.tsx",
            "app/layout.tsx",
            "next.config.js",
            "next.config.mjs",
            "next.config.ts",
            "package.json",
        }
        return any(path in known for path in required_any)

    def _sanitize_npm_project_token(self, token: str) -> str:
        lowered = token.strip().lower()
        sanitized = re.sub(r"[^a-z0-9._~-]", "-", lowered)
        sanitized = re.sub(r"-+", "-", sanitized).strip("-.")
        return sanitized or "app"

    def _normalize_command_text(self, command: str) -> str:
        normalized = str(command).strip()
        if not normalized:
            return ""

        match = re.search(
            r"(?i)(\bcreate-next-app(?:@latest)?\b\s+)(\"[^\"]+\"|'[^']+'|\S+)(.*)",
            normalized,
        )
        if not match:
            return normalized

        project_token = match.group(2)
        prefix = normalized[: match.start(2)]
        suffix = normalized[match.end(2) :]
        stripped_token = project_token.strip().strip('"').strip("'")

        if not stripped_token:
            return normalized

        if stripped_token.startswith("-") or stripped_token == ".":
            return normalized

        # `workspace` is the execution root label, not a project directory name.
        if stripped_token.lower() == "workspace":
            return f"{prefix}.{suffix}"

        safe_name = self._sanitize_npm_project_token(stripped_token)
        if safe_name == stripped_token:
            return normalized

        return f"{prefix}{safe_name}{suffix}"

    def _is_scaffold_command(self, command: str) -> bool:
        lowered = command.lower()
        return (
            "create-next-app" in lowered
            or "npm create" in lowered
            or "npm init" in lowered
            or "npx create-" in lowered
        )

    def _should_skip_command_for_workspace(
        self,
        command: str,
        workspace_context: Dict[str, Any] | None,
    ) -> bool:
        lowered = command.lower()
        known = self._workspace_known_paths(workspace_context)
        if not known:
            return False

        if "create-next-app" in lowered and self._looks_like_next_workspace(workspace_context):
            return True

        if "npm init" in lowered and "package.json" in known:
            return True

        return False

    def _enforce_command_first_execution(self, graph: DagGraph) -> None:
        if not graph.command_nodes:
            return

        command_ids = {node.node_id for node in graph.command_nodes}

        for index, node in enumerate(graph.command_nodes):
            previous = [graph.command_nodes[index - 1].node_id] if index > 0 else []
            following = [graph.command_nodes[index + 1].node_id] if index < len(graph.command_nodes) - 1 else []
            node.depends_on = previous
            node.next = following
            node.status = "READY" if not previous else "BLOCKED"
            node.task_type = "command"
            if not node.command_scope:
                node.command_scope = "workspace"

        last_command_id = graph.command_nodes[-1].node_id

        for node in graph.nodes:
            node.task_type = "agent"
            non_command_deps = [dep for dep in node.depends_on if dep not in command_ids]
            if last_command_id not in non_command_deps:
                node.depends_on = [last_command_id, *non_command_deps]
            else:
                node.depends_on = non_command_deps

            node.next = [next_id for next_id in node.next if next_id not in command_ids]
            node.status = "READY" if not node.depends_on else "BLOCKED"

        starter_agents = [node.node_id for node in graph.nodes if len(node.depends_on) == 1 and node.depends_on[0] == last_command_id]
        graph.command_nodes[-1].next = starter_agents

    def _finalize_graph(self, graph: DagGraph) -> DagGraph:
        for command_node in graph.command_nodes:
            command_node.terminal_command = self._normalize_command_text(
                command_node.terminal_command or ""
            )
        self._enforce_command_first_execution(graph)
        return build_dag(
            graph,
            workspace_context=None,
            research_brief=ResearchBrief(
                objective="",
                constraints=[],
                assumptions=[],
                risks=[],
            ),
            executor_max_span_lines=self._executor_max_context_lines(),
        )

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

    def _collect_terminal_commands(
        self,
        research_brief: ResearchBrief,
        workspace_context: Dict[str, Any] | None = None,
    ) -> List[str]:
        ordered_candidates = [
            *research_brief.setup_commands,
            *research_brief.run_commands,
            *research_brief.test_commands,
        ]

        unique_commands: List[str] = []
        seen: set[str] = set()
        for command in ordered_candidates:
            normalized = self._normalize_command_text(command)
            if not normalized or normalized in seen:
                continue
            if self._should_skip_command_for_workspace(normalized, workspace_context):
                continue
            seen.add(normalized)
            unique_commands.append(normalized)
        return unique_commands

    def _build_command_nodes(self, commands: List[str]) -> List[DagNode]:
        if not commands:
            return []

        command_nodes: List[DagNode] = []
        for index, command in enumerate(commands, start=1):
            node_id = f"CMD-{index:02d}"
            depends_on = [f"CMD-{index - 1:02d}"] if index > 1 else []
            next_nodes = [f"CMD-{index + 1:02d}"] if index < len(commands) else []
            command_nodes.append(
                DagNode(
                    node_id=node_id,
                    status="READY" if not depends_on else "BLOCKED",
                    depends_on=depends_on,
                    next=next_nodes,
                    target_file="",
                    start_line=0,
                    end_line=0,
                    mutation_intent=f"Execute command: {command}",
                    acceptance_checks=[],
                    branch_key="command-flow",
                    task_type="command",
                    terminal_command=command,
                    command_scope="workspace",
                )
            )

        return command_nodes

    def _default_targets_from_brief(self, research_brief: ResearchBrief) -> List[str]:
        extracted: List[str] = []
        for item in research_brief.recommended_structure:
            candidate = str(item).strip().strip("/")
            if not candidate:
                continue
            if candidate.endswith("/"):
                continue
            if "." not in Path(candidate).name:
                continue
            if candidate not in extracted:
                extracted.append(candidate)

        if extracted:
            return extracted[:6]

        stack = research_brief.tech_stack.lower()
        if "next.js" in stack or "react" in stack:
            return [
                "app/page.tsx",
                "app/layout.tsx",
                "app/globals.css",
                "package.json",
                "next.config.js",
            ]
        if "laravel" in stack or "php" in stack:
            return [
                "routes/web.php",
                "app/Http/Controllers/HomeController.php",
                "resources/views/welcome.blade.php",
                "composer.json",
            ]
        if "fastapi" in stack or "python" in stack:
            return [
                "app/main.py",
                "app/routes/health.py",
                "requirements.txt",
            ]
        return [
            "src/index.js",
            "src/routes/index.js",
            "package.json",
        ]

    def _fallback_plan(
        self,
        request: str,
        research_brief: ResearchBrief,
        workspace_context: Dict[str, Any] | None = None,
    ) -> DagGraph:
        commands = self._collect_terminal_commands(
            research_brief,
            workspace_context=workspace_context,
        )
        command_nodes = self._build_command_nodes(commands)
        targets = self._default_targets_from_brief(research_brief)

        trigger_depends_on: List[str] = []
        if command_nodes:
            trigger_depends_on = [command_nodes[-1].node_id]

        nodes: List[DagNode] = []
        for index, target in enumerate(targets, start=1):
            node_id = chr(ord("A") + index - 1)
            depends_on = list(trigger_depends_on) if index == 1 else [nodes[-1].node_id]
            next_nodes: List[str] = []
            if index < len(targets):
                next_nodes = [chr(ord("A") + index)]

            nodes.append(
                DagNode(
                    node_id=node_id,
                    status="READY" if not depends_on else "BLOCKED",
                    depends_on=depends_on,
                    next=next_nodes,
                    target_file=target,
                    start_line=1,
                    end_line=80,
                    mutation_intent=(
                        f"Implement requested behavior for {target} based on: {request.strip()}"
                    ),
                    acceptance_checks=[],
                    branch_key="fallback-plan",
                    task_type="agent",
                    terminal_command="",
                    command_scope="workspace",
                )
            )

        if command_nodes and nodes:
            command_nodes[-1].next = [nodes[0].node_id]

        graph = DagGraph(
            graph_id="planner-fallback",
            nodes=nodes,
            command_nodes=command_nodes,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return self._finalize_graph(graph)

    def describe_terminal_commands(
        self,
        graph: DagGraph,
        command_mode: str = "batch",
        research_brief: ResearchBrief | None = None,
        workspace_context: Dict[str, Any] | None = None,
    ) -> str:
        if research_brief is not None:
            unique_commands = self._collect_terminal_commands(
                research_brief,
                workspace_context=workspace_context,
            )
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

        for _attempt in range(3):
            response = llm_generate_text("PLANNER", prompt)
            last_response = response
            graph = self._graph_from_response(
                response,
                research_brief=research_brief,
                workspace_context=workspace_context,
            )
            if graph is not None and self._is_valid_graph(graph):
                if not graph.command_nodes:
                    graph.command_nodes = self._build_command_nodes(
                        self._collect_terminal_commands(
                            research_brief,
                            workspace_context=workspace_context,
                        )
                    )
                else:
                    normalized_commands: List[str] = []
                    for command_node in graph.command_nodes:
                        normalized = self._normalize_command_text(
                            command_node.terminal_command or ""
                        )
                        if not normalized:
                            continue
                        if self._should_skip_command_for_workspace(
                            normalized,
                            workspace_context=workspace_context,
                        ):
                            continue
                        normalized_commands.append(normalized)

                    graph.command_nodes = self._build_command_nodes(normalized_commands)
                return self._finalize_graph(graph)

            prompt = self._planner_repair_prompt(
                request,
                research_brief,
                workspace_context,
                response,
            )

        return self._fallback_plan(
            request,
            research_brief,
            workspace_context=workspace_context,
        )

    def plan_parallel_coding_assistant(
        self,
        request: str,
        research_brief: ResearchBrief,
        workspace_context: Dict[str, Any] | None = None,
    ) -> DagGraph:
        return self.plan(request, research_brief, workspace_context=workspace_context)
