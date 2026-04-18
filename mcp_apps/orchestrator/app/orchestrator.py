from __future__ import annotations

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List

from mcp_apps.orchestrator.app.planner import Planner
from mcp_apps.orchestrator.app.researcher import ResearchAgent
from mcp_apps.orchestrator.app.state_manager import StateManager
from mcp_apps.orchestrator.app import trace_exporter
from mcp_apps.orchestrator.libraries.auth.auth_adapter import bootstrap_planner_session
from mcp_clients.agent_executor.client.worker import execute_node
from mcp_clients.agent_executor.tools.flow_parser import build_flow_index, render_flow_report
from mcp_apps.orchestrator.libraries.types.contracts import ResearchBrief, SessionProfile


def _choose_next_ready_nodes(
    state: StateManager,
    current_node_id: str,
) -> List[str]:
    node = state.graph.node_by_id[current_node_id]
    next_ready = []
    for next_id in node.next:
        candidate = state.graph.node_by_id[next_id]
        if candidate.status == "READY":
            next_ready.append(next_id)
    return next_ready


def _format_delegated_command(node) -> str:
    if (
        getattr(node, "task_type", "agent") == "command"
        and getattr(node, "terminal_command", "")
    ):
        return f"command={node.terminal_command} | branch={node.branch_key}"

    if node.target_file:
        target = f"{node.target_file}:{node.start_line}-{node.end_line}"
    else:
        target = "workspace"
    return (
        f"{node.mutation_intent} | target={target} "
        f"| branch={node.branch_key}"
    )


def _compact_text(text: str, limit: int = 180) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 3]}..."


def _is_supported_workspace_file(path: Path) -> bool:
    supported_names = {
        "Dockerfile",
        "README.md",
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "tsconfig.json",
        "next.config.js",
        "next.config.mjs",
        "next.config.ts",
    }
    supported_suffixes = {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".json",
        ".md",
        ".toml",
        ".txt",
        ".yml",
        ".yaml",
        ".css",
        ".html",
        ".env",
    }
    return path.name in supported_names or path.suffix.lower() in supported_suffixes


def _should_skip_workspace_path(path: Path, root: Path) -> bool:
    excluded_parts = {
        ".git",
        ".venv",
        "node_modules",
        "dist",
        "build",
        "out",
        "coverage",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".next",
        ".turbo",
        "output",
    }
    relative_parts = path.relative_to(root).parts
    for part in relative_parts[:-1]:
        if part in excluded_parts:
            return True
        if part.startswith(".") and part not in {".gitignore", ".env", ".env.local"}:
            return True
    return False


def _file_preview(path: Path, max_lines: int = 24, max_chars: int = 1400) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

    lines = content.splitlines()
    preview = "\n".join(lines[:max_lines]).strip()
    if len(preview) > max_chars:
        preview = f"{preview[: max_chars - 3]}..."
    return preview


def _scan_workspace_context(root: Path, max_files: int = 40) -> Dict[str, Any]:
    files: List[Dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if len(files) >= max_files:
            break
        if not path.is_file():
            continue
        if _should_skip_workspace_path(path, root):
            continue
        if not _is_supported_workspace_file(path):
            continue

        relative_path = path.relative_to(root).as_posix()
        preview = _file_preview(path)
        files.append(
            {
                "path": relative_path,
                "preview": preview,
            }
        )

    return {
        "root": str(root),
        "file_count": len(files),
        "truncated": len(files) >= max_files,
        "files": files,
    }


def _workspace_root() -> Path:
    configured = os.environ.get("MCP_WORKSPACE_ROOT", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.exists():
            return candidate

    fallback = Path(__file__).resolve().parents[3] / "mcp_testbed" / "workspace"
    if fallback.exists():
        return fallback

    return Path.cwd()


def _execute_local_command(agent_id: str, node) -> dict:
    command = node.terminal_command or (
        node.acceptance_checks[0] if node.acceptance_checks else ""
    )
    if not command:
        return {
            "ok": False,
            "agent_id": agent_id,
            "node_id": node.node_id,
            "error": "Command node is missing terminal_command",
        }

    while True:
        try:
            print()
            ans = input(
                f'Would you like to execute the command: "{command}"? (Y/N) '
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            ans = 'n'
            
        if ans == 'y':
            break
        elif ans == 'n':
            return {
                "ok": False,
                "agent_id": agent_id,
                "node_id": node.node_id,
                "error": f"Command execution aborted by user: {command}",
            }

    try:
        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(_workspace_root()),
            check=True,
        )
        summary = " ".join(
            part.strip() for part in [completed.stdout, completed.stderr] if part and part.strip()
        ).strip()
        return {
            "ok": True,
            "agent_id": agent_id,
            "node_id": node.node_id,
            "status": "DONE",
            "summary": _compact_text(summary or f"command completed: {command}"),
        }
    except subprocess.CalledProcessError as exc:
        summary = (exc.stderr or exc.stdout or str(exc)).strip()
        return {
            "ok": False,
            "agent_id": agent_id,
            "node_id": node.node_id,
            "error": _compact_text(summary or str(exc)),
        }


def _run_delegated_task_with_context(
    agent_id: str,
    graph,
    node_id: str,
    abstraction_context: list[str],
    enforce_layered_design: bool,
) -> dict:
    node = graph.node_by_id[node_id]
    if getattr(node, "task_type", "agent") == "command":
        return _execute_local_command(agent_id, node)
    return execute_node(
        agent_id=agent_id,
        graph=graph,
        node_id=node_id,
        abstraction_context=abstraction_context,
        enforce_layered_design=enforce_layered_design,
    )


def _ask_yes_no(prompt: str, default_yes: bool = True) -> bool:
    if not os.isatty(0):
        env_value = os.environ.get("MCP_IMPLICIT_LAYERED_DESIGN", "1")
        return env_value.strip().lower() in {"1", "true", "yes", "on"}

    suffix = "Y/n" if default_yes else "y/N"
    while True:
        try:
            answer = input(f"{prompt} ({suffix}) ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return default_yes

        if not answer:
            return default_yes
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False


def _format_research_brief_text(research_brief: ResearchBrief) -> str:
    """Render a ResearchBrief as human-readable plain text for trace export."""
    d = research_brief.to_dict()
    lines = [f"objective: {d['objective']}"]
    for section in ("constraints", "assumptions", "risks"):
        lines.append(f"{section}:")
        for item in d[section]:
            lines.append(f"- {item}")
    if d.get("tech_stack"):
        lines.append(f"tech_stack: {d['tech_stack']}")
    for section in ("setup_commands", "run_commands", "test_commands"):
        if d.get(section):
            lines.append(f"{section}: {d[section]}")
    return "\n".join(lines)


def run_orchestrator(user_request: str) -> None:
    # Phase 0 remains the same behavior through provider adapter indirection.
    try:
        profile = bootstrap_planner_session()
    except Exception as exc:
        profile = SessionProfile(headers={}, cookie_jar={})
        print(
            "Phase 0 skipped. "
            f"Planner session bootstrap unavailable: {exc}"
        )
    print(
        "Phase 0 complete. "
        f"Captured planner session profile with {len(profile.headers)} headers."
    )

    researcher = ResearchAgent()
    research_brief = researcher.research(user_request)
    workspace_context = _scan_workspace_context(Path.cwd())

    planner = Planner()
    graph = planner.plan(user_request, research_brief, workspace_context=workspace_context)
    flow_index = build_flow_index(graph)
    command_mode = os.environ.get("MCP_COMMAND_PRESENTATION", "batch")
    enforce_layered_design = _ask_yes_no(
        "Enable implicit layered design for executor-generated code?",
        default_yes=True,
    )

    print("\n=== Workspace Scan ===")
    print(planner.describe_workspace_context(workspace_context))

    print("\n=== Planner Input ===")
    print(f"request: {user_request}")
    print(f"research objective: {research_brief.objective}")
    if research_brief.project_type:
        print(f"project type: {research_brief.project_type}")
    if research_brief.tech_stack:
        print(f"tech stack: {research_brief.tech_stack}")
    if research_brief.recommended_structure:
        print(f"recommended structure: {research_brief.recommended_structure}")
    if research_brief.setup_commands:
        print(f"setup commands: {research_brief.setup_commands}")
    if research_brief.run_commands:
        print(f"run commands: {research_brief.run_commands}")
    if research_brief.test_commands:
        print(f"test commands: {research_brief.test_commands}")
    trace_exporter.write_text(
        "planner/research_brief.json",
        json.dumps(research_brief.to_dict(), indent=2),
    )
    trace_exporter.write_text("planner/plan.json", json.dumps(graph.to_dict(), indent=2))
    command_nodes_payload = [
        {
            "node_id": node.node_id,
            "status": node.status,
            "depends_on": list(node.depends_on),
            "next": list(node.next),
            "task_type": node.task_type,
            "terminal_command": node.terminal_command,
            "command_scope": node.command_scope,
        }
        for node in graph.command_nodes
    ]
    trace_exporter.write_text(
        "planner/command_nodes.json",
        json.dumps(command_nodes_payload, indent=2),
    )
    print("\n=== Parallel Waves ===")
    print(planner.describe_parallel_waves(graph))
    print("\n=== Planner Plan ===")
    print(planner.describe_plan(graph))
    print("\n=== Planner Mermaid ===")
    print("```mermaid")
    print(planner.render_mermaid(graph))
    print("```")
    print("\n=== Source Targets ===")
    print(planner.describe_source_targets(graph))
    print("\n=== Workspace Structure ===")
    print(planner.describe_workspace_structure(graph))
    print("\n=== Terminal Commands ===")
    print(
        planner.describe_terminal_commands(
            graph,
            command_mode,
            research_brief=research_brief,
        )
    )
    print("\n=== Flow Parser ===")
    print(render_flow_report(graph))
    print(
        "\n=== Layered Design Policy ===\n"
        f"implicit_layered_design={enforce_layered_design}"
    )

    trace_exporter.write_text("planner/request.txt", user_request)
    trace_exporter.write_text(
        "planner/workspace_context.json",
        json.dumps(workspace_context, indent=2),
    )
    trace_exporter.write_text(
        "planner/workspace_context.txt",
        planner.describe_workspace_context(workspace_context),
    )
    trace_exporter.write_text(
        "planner/research_brief.txt",
        _format_research_brief_text(research_brief),
    )
    trace_exporter.write_text("planner/parallel_waves.txt", planner.describe_parallel_waves(graph))
    trace_exporter.write_text("planner/plan.txt", planner.describe_plan(graph))
    trace_exporter.write_text("planner/mermaid.mmd", planner.render_mermaid(graph))
    trace_exporter.write_text("planner/source_targets.txt", planner.describe_source_targets(graph))
    trace_exporter.write_text(
        "planner/workspace_structure.txt",
        planner.describe_workspace_structure(graph),
    )
    trace_exporter.write_text(
        "planner/terminal_commands.txt",
        planner.describe_terminal_commands(
            graph,
            command_mode,
            research_brief=research_brief,
        ),
    )
    trace_exporter.write_text("planner/command_mode.txt", command_mode)
    trace_exporter.write_text("planner/flow_parser.txt", render_flow_report(graph))
    trace_exporter.write_text(
        "planner/implicit_layered_design.txt",
        f"implicit_layered_design={enforce_layered_design}",
    )
    state = StateManager(graph=graph)

    created_agents: List[str] = []
    timeline: List[str] = []
    parallel_waves: List[str] = []
    node_agent_map: Dict[str, str] = {}
    active_agents: set[str] = set()
    file_summaries: Dict[str, List[str]] = {}
    next_agent_number = 1

    def next_agent_id() -> str:
        nonlocal next_agent_number
        agent_id = f"agent-{next_agent_number}"
        next_agent_number += 1
        return agent_id

    def register_agent(next_agent_id: str) -> None:
        if next_agent_id not in created_agents:
            created_agents.append(next_agent_id)

    def activate_agent(agent_id: str) -> None:
        active_agents.add(agent_id)

    def retire_agent(agent_id: str, reason: str) -> None:
        if agent_id in active_agents:
            active_agents.remove(agent_id)
            record(f"retire {agent_id} | reason={reason}")

    def abstraction_context_for_node(node_id: str) -> List[str]:
        node = graph.node_by_id[node_id]
        if not node.target_file:
            return []
        entries = file_summaries.get(node.target_file, [])
        return entries[-6:]

    def select_executor_for_node(node_id: str) -> tuple[str, bool]:
        node = graph.node_by_id[node_id]
        meta = flow_index[node_id]

        if meta.is_merge:
            for dep in node.depends_on:
                dep_agent = node_agent_map.get(dep)
                if dep_agent:
                    retire_agent(dep_agent, f"merge into {node_id}")

            merged_agent = next_agent_id()
            register_agent(merged_agent)
            activate_agent(merged_agent)
            return merged_agent, True

        if meta.requires_new_executor:
            fresh_agent = next_agent_id()
            register_agent(fresh_agent)
            activate_agent(fresh_agent)
            return fresh_agent, True

        if not node.depends_on:
            fresh_agent = next_agent_id()
            register_agent(fresh_agent)
            activate_agent(fresh_agent)
            return fresh_agent, True

        parent_id = node.depends_on[0]
        parent_agent = node_agent_map.get(parent_id)
        if parent_agent:
            return parent_agent, False

        fresh_agent = next_agent_id()
        register_agent(fresh_agent)
        activate_agent(fresh_agent)
        return fresh_agent, True

    def record(message: str) -> None:
        timeline.append(f"{len(timeline) + 1}. {message}")

    def emit_timeline() -> None:
        print("\n=== Agent Timeline ===")
        print("\n".join(timeline))
        print(f"Agents used (ordered): {', '.join(created_agents)}")
        print(f"Total agents used: {len(created_agents)}")
        trace_exporter.write_text("planner/agent_timeline.txt", "\n".join(timeline))

    if graph.command_nodes:
        command_queue_lines = []
        for index, node in enumerate(graph.command_nodes, start=1):
            line = (
                f"{index}. {node.node_id} "
                f"[{node.command_scope}] {node.terminal_command}"
            )
            command_queue_lines.append(line)
        print("\n=== Command Queue ===")
        print("\n".join(command_queue_lines))
        trace_exporter.write_text("planner/command_queue.txt", "\n".join(command_queue_lines))

        record(f"command phase start -> {', '.join(node.node_id for node in graph.command_nodes)}")
        for node in graph.command_nodes:
            command_agent_id = next_agent_id()
            register_agent(command_agent_id)
            activate_agent(command_agent_id)
            delegated = _format_delegated_command(node)
            record(
                f"spawn {command_agent_id} for command node {node.node_id} "
                f"| delegated_command={delegated}"
            )
            record(
                f"dispatch {command_agent_id} -> command node {node.node_id} "
                f"| delegated_command={delegated}"
            )
            response = _run_delegated_task_with_context(
                agent_id=command_agent_id,
                graph=graph,
                node_id=node.node_id,
                abstraction_context=[],
                enforce_layered_design=enforce_layered_design,
            )
            if not response["ok"]:
                error_msg = response.get("error", "unknown error")
                print(
                    f"\n[WARN] Agent {command_agent_id} failed "
                    f"for command node {node.node_id}: {error_msg}"
                )
                record(
                    f"FAILED {command_agent_id} -> command node {node.node_id} "
                    f"| error={_compact_text(error_msg)}"
                )
            else:
                response_summary = _compact_text(response["summary"])
                record(
                    f"complete {command_agent_id} -> command node {node.node_id} "
                    f"| summary={response_summary}"
                )
            state.mark_done(node.node_id)
            retire_agent(command_agent_id, f"command node {node.node_id} complete")
        record("command phase complete")

    ready_wave = [node.node_id for node in graph.nodes if node.status == "READY"]

    while ready_wave:
        wave_label = f"Wave {len(parallel_waves) + 1}: {', '.join(ready_wave)}"
        parallel_waves.append(wave_label)
        record(f"wave {len(parallel_waves)} start -> {', '.join(ready_wave)}")

        if len(ready_wave) > 1:
            print(f"Parallel wave {len(parallel_waves)} active: {', '.join(ready_wave)}")

        queued_wave = list(ready_wave)
        for queued_node_id in queued_wave:
            record(f"queue {queued_node_id}")

        with ThreadPoolExecutor(max_workers=len(ready_wave)) as pool:
            futures = []
            for node_id in ready_wave:
                node = graph.node_by_id[node_id]
                agent_id, spawned = select_executor_for_node(node_id)
                if spawned:
                    delegated = _format_delegated_command(node)
                    record(
                        f"spawn {agent_id} for node {node_id} "
                        f"| delegated_command={delegated}"
                    )
                else:
                    delegated = _format_delegated_command(node)
                    record(
                        f"reuse {agent_id} for node {node_id} "
                        f"| delegated_command={delegated}"
                    )

                context_lines = abstraction_context_for_node(node_id)
                record(
                    f"dispatch {agent_id} -> node {node_id} | context_items={len(context_lines)}"
                )
                futures.append(
                    (
                        agent_id,
                        node_id,
                        pool.submit(
                            _run_delegated_task_with_context,
                            agent_id,
                            graph,
                            node_id,
                            context_lines,
                            enforce_layered_design,
                        ),
                    )
                )

            for agent_id, node_id, fut in futures:
                response = fut.result()
                if not response["ok"]:
                    error_msg = response.get("error", "unknown error")
                    print(f"\n[WARN] Agent {agent_id} failed for node {node_id}: {error_msg}")
                    record(
                        f"FAILED {agent_id} -> node {node_id} "
                        f"| error={_compact_text(error_msg)}"
                    )
                else:
                    node_summary = _compact_text(response["summary"])
                    record(
                        f"complete {agent_id} -> node {node_id} "
                        f"| summary={node_summary}"
                    )
                    node = graph.node_by_id[node_id]
                    node_agent_map[node_id] = agent_id

                    summary_text = response.get("artifact_summary_text", "")
                    if (
                        isinstance(summary_text, str)
                        and summary_text.strip()
                        and node.target_file
                    ):
                        file_summaries.setdefault(node.target_file, []).append(summary_text)
                        record(f"summary {agent_id} -> {node.target_file}")

                    if not node.next:
                        retire_agent(agent_id, f"flow ended at {node_id}")

                # Always mark done so downstream nodes aren't permanently blocked
                state.mark_done(node_id)

        state.unblock_ready_nodes()
        ready_wave = [node.node_id for node in graph.nodes if node.status == "READY"]
        record(f"wave {len(parallel_waves)} complete")

    print("\n=== Parallel Waves ===")
    print("\n".join(parallel_waves))
    trace_exporter.write_text("planner/parallel_waves.txt", "\n".join(parallel_waves))
    abstraction_lines = ["Node Abstraction Summaries:"]
    for file_path, summaries in sorted(file_summaries.items()):
        abstraction_lines.append(f"- {file_path}")
        for summary in summaries:
            abstraction_lines.append(f"  {summary}")
    trace_exporter.write_text("planner/abstraction_summaries.txt", "\n".join(abstraction_lines))
    emit_timeline()
    print("Parallel coding assistant execution complete.")
