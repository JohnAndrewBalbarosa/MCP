from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import List

from mcp_apps.orchestrator.app.planner import Planner
from mcp_apps.orchestrator.app.researcher import ResearchAgent
from mcp_apps.orchestrator.app.state_manager import StateManager
from mcp_apps.orchestrator.libraries.auth.auth_adapter import bootstrap_planner_session
from mcp_clients.agent_executor.client.agent_factory import run_ephemeral_agent


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


def run_orchestrator(user_request: str) -> None:
    # Phase 0 remains the same behavior through provider adapter indirection.
    profile = bootstrap_planner_session()
    print(f"Phase 0 complete. Captured planner session profile with {len(profile.headers)} headers.")

    researcher = ResearchAgent()
    research_brief = researcher.research(user_request)

    planner = Planner()
    graph = planner.plan(user_request, research_brief)
    print("\n=== Planner Input ===")
    print(f"request: {user_request}")
    print(f"research objective: {research_brief.objective}")
    print("\n=== Planner Plan ===")
    print(planner.describe_plan(graph))
    print("\n=== Planner Mermaid ===")
    print("```mermaid")
    print(planner.render_mermaid(graph))
    print("```")
    state = StateManager(graph=graph)

    entry = next(node.node_id for node in graph.nodes if node.status == "READY")
    current_node = entry
    agent_id = "agent-1"
    created_agents: List[str] = []
    timeline: List[str] = []

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

    register_agent(agent_id)
    record(f"spawn {agent_id} for node {current_node}")

    while True:
        node = graph.node_by_id[current_node]
        record(f"dispatch {agent_id} -> node {current_node} | delegated_command={_format_delegated_command(node)}")
        result = run_ephemeral_agent(agent_id=agent_id, graph=graph, node_id=current_node)
        if not result["ok"]:
            raise RuntimeError(f"Agent failed for node {current_node}: {result['error']}")
        record(f"complete {agent_id} -> node {current_node} | summary={result['summary']}")

        state.mark_done(current_node)
        state.unblock_ready_nodes()

        next_ready = _choose_next_ready_nodes(state, current_node)

        if len(next_ready) == 0:
            emit_timeline()
            print("Execution complete: no remaining ready nodes.")
            return

        if len(next_ready) == 1:
            current_node = next_ready[0]
            continue

        # Y-section: terminate current worker and fan-out.
        print(f"Y-section at node {current_node}. Terminating {agent_id}.")
        with ThreadPoolExecutor(max_workers=len(next_ready)) as pool:
            futures = []
            for idx, node_id in enumerate(next_ready):
                next_agent_id = f"agent-{idx + 2}"
                register_agent(next_agent_id)
                branch_node = graph.node_by_id[node_id]
                record(f"spawn {next_agent_id} for node {node_id} | delegated_command={_format_delegated_command(branch_node)}")
                futures.append((next_agent_id, node_id, pool.submit(run_ephemeral_agent, next_agent_id, graph, node_id)))
            for next_agent_id, node_id, fut in futures:
                response = fut.result()
                if not response["ok"]:
                    raise RuntimeError(f"Branch agent failed: {response['error']}")
                record(f"complete {next_agent_id} -> node {node_id} | summary={response['summary']}")
        emit_timeline()
        print("Parallel branch execution complete.")
        return
