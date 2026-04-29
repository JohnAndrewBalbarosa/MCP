from __future__ import annotations

import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List

from mcp_apps.orchestrator.app.planner import Planner
from mcp_apps.orchestrator.app.researcher import ResearchAgent
from mcp_apps.orchestrator.app.state_manager import StateManager
from mcp_apps.orchestrator.app.context_compactor import compact_branch_context
from mcp_apps.orchestrator.app import trace_exporter
from mcp_apps.orchestrator.libraries.auth.playwright_setup import bootstrap_planner_session
from mcp_clients.agent_executor.client.worker import execute_node
from mcp_clients.agent_executor.tools.flow_parser import build_flow_index, render_flow_report
from mcp_apps.orchestrator.libraries.types.contracts import ResearchBrief, SessionProfile


_COMMAND_WORKING_DIR: Path | None = None

_MAX_PREVIEW_LINES = 24
_MAX_PREVIEW_CHARS = 1_400
_MAX_DIR_ENTRIES   = 60
_MAX_SCAN_FILES    = 40


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


def _normalize_command_for_execution(command: str) -> str:
    normalized = str(command).strip()
    if not normalized:
        return ""

    match = re.search(
        r"(?i)(\bcreate-next-app(?:@latest)?\b\s+)(\"[^\"]+\"|'[^']+'|\S+)(.*)",
        normalized,
    )
    if not match:
        return normalized

    project_token = match.group(2).strip().strip('"').strip("'")
    if not project_token or project_token.startswith("-") or project_token == ".":
        return normalized

    # Final safety net: do not use workspace label as create-next-app project folder.
    if project_token.lower() == "workspace":
        return f"{normalized[: match.start(2)]}.{normalized[match.end(2):]}"

    safe = re.sub(r"[^a-z0-9._~-]", "-", project_token.strip().lower())
    safe = re.sub(r"-+", "-", safe).strip("-.") or "app"
    if safe == project_token:
        return normalized
    return f"{normalized[: match.start(2)]}{safe}{normalized[match.end(2):]}"


def _is_valid_npm_package_name(name: str) -> bool:
    candidate = name.strip()
    if not candidate:
        return False
    if candidate.startswith(".") or candidate.startswith("_"):
        return False
    return re.match(r"^[a-z0-9][a-z0-9._~-]*$", candidate) is not None


def _invalid_cwd_for_next_dot_target(command: str, cwd: Path) -> str | None:
    normalized = str(command).strip()
    if not normalized:
        return None

    match = re.search(
        r"(?i)\bcreate-next-app(?:@latest)?\b\s+(\"[^\"]+\"|'[^']+'|\S+)",
        normalized,
    )
    if not match:
        return None

    target = match.group(1).strip().strip('"').strip("'")
    if target != ".":
        return None

    folder_name = cwd.name.strip()
    if _is_valid_npm_package_name(folder_name):
        return None

    return (
        "Cannot scaffold with create-next-app target '.' from this directory because "
        f"its folder name '{folder_name}' is not a valid npm package name. "
        "Use a lowercase workspace directory name (for example 'workspace') "
        "or run create-next-app with an explicit valid target folder."
    )


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


def _file_preview(path: Path, max_lines: int = _MAX_PREVIEW_LINES, max_chars: int = _MAX_PREVIEW_CHARS) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

    lines = content.splitlines()
    preview = "\n".join(lines[:max_lines]).strip()
    if len(preview) > max_chars:
        preview = f"{preview[: max_chars - 3]}..."
    return preview


def _current_directory_entries(root: Path, max_entries: int = _MAX_DIR_ENTRIES) -> List[str]:
    entries: List[str] = []
    try:
        for path in sorted(root.iterdir(), key=lambda p: p.name.lower()):
            marker = "/" if path.is_dir() else ""
            entries.append(f"{path.name}{marker}")
            if len(entries) >= max_entries:
                break
    except Exception:
        return []
    return entries


def _scan_workspace_context(root: Path, max_files: int = _MAX_SCAN_FILES) -> Dict[str, Any]:
    cwd_entries = _current_directory_entries(root)
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
        "cwd_entries": cwd_entries,
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


def _active_command_working_dir() -> Path:
    global _COMMAND_WORKING_DIR
    if _COMMAND_WORKING_DIR is None:
        _COMMAND_WORKING_DIR = Path.cwd().resolve()
    return _COMMAND_WORKING_DIR


def _apply_cd_command(command: str) -> str | None:
    global _COMMAND_WORKING_DIR

    match = re.match(r"^\s*cd\s+(.+?)\s*$", command, flags=re.IGNORECASE)
    if not match:
        return None

    raw_target = match.group(1).strip().strip('"').strip("'")
    if not raw_target:
        return "cd command missing target path"

    base = _active_command_working_dir()
    candidate = Path(raw_target)
    target = candidate if candidate.is_absolute() else (base / candidate)
    target = target.resolve()

    if not target.exists() or not target.is_dir():
        return f"cd target does not exist: {target}"

    _COMMAND_WORKING_DIR = target
    return f"cwd changed to {target}"


def _execute_local_command(agent_id: str, node) -> dict:
    raw_command = node.terminal_command or (
        node.acceptance_checks[0] if node.acceptance_checks else ""
    )
    command = _normalize_command_for_execution(raw_command)
    if command and raw_command and command != raw_command:
        node.terminal_command = command
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

    cd_result = _apply_cd_command(command)
    if cd_result is not None:
        return {
            "ok": not cd_result.startswith("cd target does not exist") and not cd_result.startswith("cd command missing"),
            "agent_id": agent_id,
            "node_id": node.node_id,
            "status": "DONE" if not cd_result.startswith("cd target does not exist") and not cd_result.startswith("cd command missing") else "FAILED",
            "summary": cd_result,
            "error": cd_result if cd_result.startswith("cd target does not exist") or cd_result.startswith("cd command missing") else "",
        }

    working_dir = _active_command_working_dir()
    invalid_cwd_message = _invalid_cwd_for_next_dot_target(command, working_dir)
    if invalid_cwd_message:
        return {
            "ok": False,
            "agent_id": agent_id,
            "node_id": node.node_id,
            "error": invalid_cwd_message,
        }

    try:
        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(working_dir),
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
    global _COMMAND_WORKING_DIR

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

    workspace_root = _workspace_root().resolve()
    _COMMAND_WORKING_DIR = workspace_root

    researcher = ResearchAgent()
    research_brief = researcher.research(user_request)
    workspace_context = _scan_workspace_context(workspace_root)

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
            workspace_context=workspace_context,
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
            workspace_context=workspace_context,
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
    file_summaries: Dict[str, List[dict]] = {}
    node_compactions: Dict[str, dict] = {}
    agent_fork_origin: Dict[str, str] = {}
    fork_agent_stats: Dict[str, Dict[str, Any]] = {}
    compaction_events: List[Dict[str, Any]] = []
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

    def _fork_origin_for_node(node_id: str) -> str | None:
        node = graph.node_by_id[node_id]
        if len(node.depends_on) != 1:
            return None
        parent = graph.node_by_id[node.depends_on[0]]
        if (getattr(parent, "outgoing_flow_count", 0) or len(parent.next)) > 1:
            return parent.node_id
        return None

    def _register_fork_spawn(agent_id: str, node_id: str) -> None:
        fork_origin = _fork_origin_for_node(node_id)
        if not fork_origin:
            return
        agent_fork_origin[agent_id] = fork_origin
        stats = fork_agent_stats.setdefault(
            fork_origin,
            {"generated": 0, "retired": 0, "children": [], "branch_width": graph.node_by_id[fork_origin].outgoing_flow_count},
        )
        stats["generated"] += 1
        if node_id not in stats["children"]:
            stats["children"].append(node_id)

    def retire_agent(agent_id: str, reason: str) -> None:
        if agent_id in active_agents:
            active_agents.remove(agent_id)
            record(f"retire {agent_id} | reason={reason}")
        fork_origin = agent_fork_origin.get(agent_id)
        if fork_origin:
            stats = fork_agent_stats.setdefault(
                fork_origin,
                {"generated": 0, "retired": 0, "children": [], "branch_width": graph.node_by_id[fork_origin].outgoing_flow_count},
            )
            stats["retired"] += 1

    def abstraction_context_for_node(node_id: str) -> List[str]:
        node = graph.node_by_id[node_id]
        context_items: List[str] = []
        for dep_id in node.depends_on:
            packet = node_compactions.get(dep_id)
            if not packet:
                continue
            ground_truth = str(packet.get("next_agent_ground_truth", "")).strip()
            if ground_truth:
                context_items.append(ground_truth)

        if node.target_file:
            entries = file_summaries.get(node.target_file, [])
            context_items.extend(
                str(entry.get("next_agent_ground_truth", "")).strip()
                for entry in entries[-6:]
                if str(entry.get("next_agent_ground_truth", "")).strip()
            )

        deduped: List[str] = []
        seen: set[str] = set()
        for item in context_items:
            if item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped[-6:]

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

        if getattr(node, "requires_fresh_agent", False) or meta.requires_new_executor:
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
                    _register_fork_spawn(agent_id, node_id)
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
                    artifact_summary = response.get("artifact_summary", {})
                    if node.target_file and isinstance(artifact_summary, dict):
                        handoff_packet = compact_branch_context(
                            node_id=node_id,
                            target_file=node.target_file,
                            branch_outputs=[summary_text] if isinstance(summary_text, str) and summary_text.strip() else [node_summary],
                            artifact_summary=artifact_summary,
                            node_metadata={
                                "requires_fresh_agent": getattr(node, "requires_fresh_agent", False),
                                "merge_role": getattr(node, "merge_role", "linear"),
                                "incoming_flow_count": getattr(node, "incoming_flow_count", 0),
                            },
                            artifact_snapshot=str(artifact_summary.get("replacement_head", "")),
                        )
                        node_compactions[node_id] = handoff_packet
                        file_summaries.setdefault(node.target_file, []).append(handoff_packet)
                        compaction_events.append(
                            {
                                "node_id": node_id,
                                "target_file": node.target_file,
                                "requires_fresh_agent": handoff_packet.get("requires_fresh_agent", False),
                                "function_header_count": len(handoff_packet.get("function_headers", [])),
                                "summary": handoff_packet.get("branch_summary", ""),
                            }
                        )
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
            abstraction_lines.append(
                f"  {summary.get('next_agent_ground_truth', '').strip()}"
            )
    trace_exporter.write_text("planner/abstraction_summaries.txt", "\n".join(abstraction_lines))

    fork_lines = ["Fork Agent Report:"]
    if not fork_agent_stats:
        fork_lines.append("none")
    else:
        for fork_node, stats in sorted(fork_agent_stats.items()):
            active_count = max(0, int(stats["generated"]) - int(stats["retired"]))
            children = ", ".join(stats.get("children", [])) or "none"
            fork_lines.append(
                f"- {fork_node}: generated={stats['generated']} retired={stats['retired']} "
                f"active={active_count} branch_width={stats.get('branch_width', 0)} children={children}"
            )
    print("\n=== Fork Agent Report ===")
    print("\n".join(fork_lines))
    trace_exporter.write_text("planner/fork_agent_report.txt", "\n".join(fork_lines))
    trace_exporter.write_text("planner/fork_agent_report.json", json.dumps(fork_agent_stats, indent=2))

    compaction_lines = ["Compaction Report:"]
    if not compaction_events:
        compaction_lines.append("none")
    else:
        for event in compaction_events:
            compaction_lines.append(
                f"- node={event['node_id']} file={event['target_file']} "
                f"fresh_agent={event['requires_fresh_agent']} "
                f"function_headers={event['function_header_count']} "
                f"summary={event['summary']}"
            )
    print("\n=== Compaction Report ===")
    print("\n".join(compaction_lines))
    trace_exporter.write_text("planner/compaction_report.txt", "\n".join(compaction_lines))
    trace_exporter.write_text("planner/compaction_report.json", json.dumps(compaction_events, indent=2))
    emit_timeline()
    print("Parallel coding assistant execution complete.")
