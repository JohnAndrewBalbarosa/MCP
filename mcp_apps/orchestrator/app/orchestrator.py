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


def run_orchestrator(user_request: str) -> None:
    # Phase 0 remains the same behavior through provider adapter indirection.
    profile = bootstrap_planner_session()
    print(f"Phase 0 complete. Captured profile: {profile.base_url}")

    researcher = ResearchAgent()
    research_brief = researcher.research(user_request)

    planner = Planner()
    graph = planner.plan(user_request, research_brief)
    state = StateManager(graph=graph)

    entry = next(node.node_id for node in graph.nodes if node.status == "READY")
    current_node = entry
    agent_id = "agent-1"

    while True:
        result = run_ephemeral_agent(agent_id=agent_id, graph=graph, node_id=current_node)
        if not result["ok"]:
            raise RuntimeError(f"Agent failed for node {current_node}: {result['error']}")

        state.mark_done(current_node)
        state.unblock_ready_nodes()

        next_ready = _choose_next_ready_nodes(state, current_node)

        if len(next_ready) == 0:
            print("Execution complete: no remaining ready nodes.")
            return

        if len(next_ready) == 1:
            current_node = next_ready[0]
            continue

        # Y-section: terminate current worker and fan-out.
        print(f"Y-section at node {current_node}. Terminating {agent_id}.")
        with ThreadPoolExecutor(max_workers=len(next_ready)) as pool:
            futures = [
                pool.submit(run_ephemeral_agent, f"agent-{idx+2}", graph, node_id)
                for idx, node_id in enumerate(next_ready)
            ]
            for fut in futures:
                response = fut.result()
                if not response["ok"]:
                    raise RuntimeError(f"Branch agent failed: {response['error']}")
        print("Parallel branch execution complete.")
        return
