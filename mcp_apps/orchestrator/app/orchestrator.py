from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from typing import List

from mcp_apps.orchestrator.app.planner import Planner
from mcp_apps.orchestrator.app.researcher import ResearchAgent
from mcp_apps.orchestrator.app.state_manager import StateManager
from mcp_apps.orchestrator.app import trace_exporter
from mcp_apps.orchestrator.libraries.auth.auth_adapter import bootstrap_planner_session
from mcp_clients.agent_executor.client.agent_factory import run_ephemeral_agent
from mcp_apps.orchestrator.libraries.types.contracts import ResearchBrief


def _choose_next_ready_nodes(state: StateManager, current_node_id: str) -> List[str]:
    node = state.graph.node_by_id[current_node_id]
    next_ready = []
    for next_id in node.next:
        candidate = state.graph.node_by_id[next_id]
        if candidate.status == "READY":
            next_ready.append(next_id)
    return next_ready


def _format_delegated_command(node) -> str:
    return (
        f"{node.mutation_intent} | target={node.target_file}:{node.start_line}-{node.end_line} "
        f"| branch={node.branch_key}"
    )


def _is_parallel_coding_request(user_request: str) -> bool:
    normalized = user_request.lower()
    has_parallel_terms = any(
        term in normalized
        for term in ["parallel", "multiple tasks", "multiple task", "parallelism", "at once"]
    )
    has_coding_terms = any(
        term in normalized for term in ["code", "folder", "file", "assistant", "codex", "vs code"]
    )
    return has_parallel_terms and has_coding_terms


def _describe_research_brief(research_brief: ResearchBrief) -> str:
    lines = [f"objective: {research_brief.objective}"]
    lines.append("constraints:")
    for item in research_brief.constraints:
        lines.append(f"- {item}")
    lines.append("assumptions:")
    for item in research_brief.assumptions:
        lines.append(f"- {item}")
    lines.append("risks:")
    for item in research_brief.risks:
        lines.append(f"- {item}")
    return "\n".join(lines)


def run_orchestrator(user_request: str) -> None:
    # Phase 0 remains the same behavior through provider adapter indirection.
    profile = bootstrap_planner_session()
    print(f"Phase 0 complete. Captured planner session profile with {len(profile.headers)} headers.")

    researcher = ResearchAgent()
    research_brief = researcher.research(user_request)

    planner = Planner()
    parallel_coding_mode = _is_parallel_coding_request(user_request)
    graph = (
        planner.plan_parallel_coding_assistant(user_request, research_brief)
        if parallel_coding_mode
        else planner.plan(user_request, research_brief)
    )
    command_mode = os.environ.get("MCP_COMMAND_PRESENTATION", "batch")

    print("\n=== Planner Input ===")
    print(f"request: {user_request}")
    print(f"research objective: {research_brief.objective}")
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
            include_publish_commands=parallel_coding_mode,
        )
    )

    trace_exporter.write_text("planner/request.txt", user_request)
    trace_exporter.write_text("planner/research_brief.txt", _describe_research_brief(research_brief))
    trace_exporter.write_text("planner/parallel_waves.txt", planner.describe_parallel_waves(graph))
    trace_exporter.write_text("planner/plan.txt", planner.describe_plan(graph))
    trace_exporter.write_text("planner/mermaid.mmd", planner.render_mermaid(graph))
    trace_exporter.write_text("planner/source_targets.txt", planner.describe_source_targets(graph))
    trace_exporter.write_text("planner/workspace_structure.txt", planner.describe_workspace_structure(graph))
    trace_exporter.write_text(
        "planner/terminal_commands.txt",
        planner.describe_terminal_commands(
            graph,
            command_mode,
            include_publish_commands=parallel_coding_mode,
        ),
    )
    trace_exporter.write_text("planner/command_mode.txt", command_mode)
    state = StateManager(graph=graph)

    agent_id = "agent-1"
    created_agents: List[str] = []
    timeline: List[str] = []
    parallel_waves: List[str] = []
    next_agent_number = 1

    def register_agent(next_agent_id: str) -> None:
        if next_agent_id not in created_agents:
            created_agents.append(next_agent_id)

    def record(message: str) -> None:
        timeline.append(f"{len(timeline) + 1}. {message}")

    def emit_timeline() -> None:
        print("\n=== Agent Timeline ===")
        print("\n".join(timeline))
        print(f"Agents used (ordered): {', '.join(created_agents)}")
        print(f"Total agents used: {len(created_agents)}")
        trace_exporter.write_text("planner/agent_timeline.txt", "\n".join(timeline))

    register_agent(agent_id)
    ready_wave = [node.node_id for node in graph.nodes if node.status == "READY"]

    while ready_wave:
        wave_label = f"Wave {len(parallel_waves) + 1}: {', '.join(ready_wave)}"
        parallel_waves.append(wave_label)
        record(f"wave {len(parallel_waves)} start -> {', '.join(ready_wave)}")

        if len(ready_wave) > 1:
            print(f"Parallel wave {len(parallel_waves)} active: {', '.join(ready_wave)}")

        with ThreadPoolExecutor(max_workers=len(ready_wave)) as pool:
            futures = []
            for node_id in ready_wave:
                agent_id = f"agent-{next_agent_number}"
                next_agent_number += 1
                register_agent(agent_id)
                node = graph.node_by_id[node_id]
                record(
                    f"spawn {agent_id} for node {node_id} | delegated_command={_format_delegated_command(node)}"
                )
                record(f"dispatch {agent_id} -> node {node_id} | delegated_command={_format_delegated_command(node)}")
                futures.append((agent_id, node_id, pool.submit(run_ephemeral_agent, agent_id, graph, node_id)))

            for agent_id, node_id, fut in futures:
                response = fut.result()
                if not response["ok"]:
                    raise RuntimeError(f"Agent failed for node {node_id}: {response['error']}")
                state.mark_done(node_id)
                record(f"complete {agent_id} -> node {node_id} | summary={response['summary']}")

        state.unblock_ready_nodes()
        ready_wave = [node.node_id for node in graph.nodes if node.status == "READY"]
        record(f"wave {len(parallel_waves)} complete")

    print("\n=== Parallel Waves ===")
    print("\n".join(parallel_waves))
    trace_exporter.write_text("planner/parallel_waves.txt", "\n".join(parallel_waves))
    emit_timeline()
    print("Parallel coding assistant execution complete.")
