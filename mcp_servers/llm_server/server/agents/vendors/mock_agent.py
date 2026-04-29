from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import List

from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntime

_MOCK_LOG = logging.getLogger(__name__)


def _user_request(prompt: str) -> str:
    """Extract the user request from a prompt containing 'User request: <text>'."""
    match = re.search(r"User request:\s*(.+)$", prompt, flags=re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def _research_response(request: str) -> str:
    """Return a deterministic JSON research brief for the parallel-scheduler demo."""
    payload = {
        "objective": "Build a parallel scheduler demo with a merge prerequisite and reporting artifacts.",
        "constraints": [
            "Keep the output inside Workspace/parallel_scheduler_demo.",
            "Demonstrate a fork node, two parallel children, and a join node.",
            "Report generated and deleted agent counts together with compaction summaries.",
        ],
        "assumptions": [
            "The demo should run locally without external services.",
            "Files can be created from scratch under the configured workspace root.",
        ],
        "risks": [
            "If the sample files already exist they must be recreated to keep bounded writes safe.",
        ],
        "project_type": "Python demo package",
        "recommended_structure": [
            "parallel_scheduler_demo/node_models.py",
            "parallel_scheduler_demo/prerequisite_counter.py",
            "parallel_scheduler_demo/fork_report.py",
            "parallel_scheduler_demo/demo_runner.py",
        ],
        "tech_stack": "Python",
        "setup_commands": [],
        "run_commands": [],
        "test_commands": [],
    }
    if request:
        payload["assumptions"].append(f"Requested scenario: {request}")
    return json.dumps(payload, indent=2)


def _planner_response() -> str:
    """Return a deterministic JSON DAG for the parallel-scheduler demo."""
    payload = {
        "graph_id": "parallel-scheduler-demo",
        "created_at": "2026-04-22T00:00:00Z",
        "nodes": [
            {
                "node_id": "A",
                "status": "READY",
                "depends_on": [],
                "next": ["B", "C"],
                "target_file": "parallel_scheduler_demo/node_models.py",
                "start_line": 1,
                "end_line": 1,
                "mutation_intent": "Create shared workflow node models and a sample graph that downstream files will consume.",
                "acceptance_checks": [
                    "Defines WorkflowNode.",
                    "Defines sample_graph().",
                ],
                "branch_key": "root",
                "outgoing_flow_count": 2,
                "incoming_flow_count": 0,
                "task_type": "agent",
                "terminal_command": "",
                "command_scope": "workspace",
            },
            {
                "node_id": "B",
                "status": "BLOCKED",
                "depends_on": ["A"],
                "next": ["D"],
                "target_file": "parallel_scheduler_demo/prerequisite_counter.py",
                "start_line": 1,
                "end_line": 1,
                "mutation_intent": "Create readiness logic that unlocks a node only when its incoming prerequisites are fully satisfied.",
                "acceptance_checks": [
                    "Computes completed prerequisite counts.",
                    "Returns ready nodes.",
                ],
                "branch_key": "prerequisites",
                "outgoing_flow_count": 1,
                "incoming_flow_count": 1,
                "task_type": "agent",
                "terminal_command": "",
                "command_scope": "workspace",
            },
            {
                "node_id": "C",
                "status": "BLOCKED",
                "depends_on": ["A"],
                "next": ["D"],
                "target_file": "parallel_scheduler_demo/fork_report.py",
                "start_line": 1,
                "end_line": 1,
                "mutation_intent": "Create fork lifecycle reporting for generated agents, deleted agents, and compaction events.",
                "acceptance_checks": [
                    "Reports generated and deleted counts for fork nodes.",
                    "Summarizes compaction events.",
                ],
                "branch_key": "reporting",
                "outgoing_flow_count": 1,
                "incoming_flow_count": 1,
                "task_type": "agent",
                "terminal_command": "",
                "command_scope": "workspace",
            },
            {
                "node_id": "D",
                "status": "BLOCKED",
                "depends_on": ["B", "C"],
                "next": [],
                "target_file": "parallel_scheduler_demo/demo_runner.py",
                "start_line": 1,
                "end_line": 1,
                "mutation_intent": "Create a runnable merge-stage demo that imports both branches and prints the scheduling result as JSON.",
                "acceptance_checks": [
                    "Imports both branch modules.",
                    "Prints ready nodes after the join.",
                ],
                "branch_key": "merge",
                "outgoing_flow_count": 0,
                "incoming_flow_count": 2,
                "task_type": "agent",
                "terminal_command": "",
                "command_scope": "workspace",
            },
        ],
        "command_nodes": [],
    }
    return json.dumps(payload, indent=2)


def _executor_target(prompt: str) -> str:
    """Extract the target file path from a prompt containing 'File: <path>'."""
    match = re.search(r"^File:\s+(.+)$", prompt, flags=re.MULTILINE)
    if not match:
        _MOCK_LOG.debug("_executor_target: no 'File:' line found in prompt")
        return ""
    return match.group(1).strip()


def _python_source_for(target_file: str) -> str:
    """Return hardcoded Python source for a known demo target file path."""
    normalized = Path(target_file).as_posix().lower()

    if normalized.endswith("parallel_scheduler_demo/node_models.py"):
        return """from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowNode:
    node_id: str
    depends_on: tuple[str, ...] = ()
    next_nodes: tuple[str, ...] = ()

    @property
    def outgoing_edge_count(self) -> int:
        return len(self.next_nodes)

    @property
    def incoming_edge_count(self) -> int:
        return len(self.depends_on)


def map_nodes(nodes: list[WorkflowNode]) -> dict[str, WorkflowNode]:
    return {node.node_id: node for node in nodes}


def sample_graph() -> list[WorkflowNode]:
    return [
        WorkflowNode("A", (), ("B", "C")),
        WorkflowNode("B", ("A",), ("D",)),
        WorkflowNode("C", ("A",), ("D",)),
        WorkflowNode("D", ("B", "C"), ()),
    ]
"""

    if normalized.endswith("parallel_scheduler_demo/prerequisite_counter.py"):
        return """from __future__ import annotations

from node_models import WorkflowNode


def completed_prerequisite_count(node: WorkflowNode, finished_nodes: set[str]) -> int:
    return sum(1 for dependency in node.depends_on if dependency in finished_nodes)


def ready_nodes(nodes: list[WorkflowNode], finished_nodes: set[str]) -> list[WorkflowNode]:
    ready: list[WorkflowNode] = []
    finished_lookup = set(finished_nodes)
    for node in nodes:
        if node.node_id in finished_lookup:
            continue
        if node.incoming_edge_count == 0:
            ready.append(node)
            continue
        if completed_prerequisite_count(node, finished_lookup) == node.incoming_edge_count:
            ready.append(node)
    return ready


def blocked_reason(node: WorkflowNode, finished_nodes: set[str]) -> str:
    completed = completed_prerequisite_count(node, finished_nodes)
    return (
        f"{node.node_id} waits for {node.incoming_edge_count} prerequisites; "
        f"{completed} adjacent upstream nodes are finished."
    )
"""

    if normalized.endswith("parallel_scheduler_demo/fork_report.py"):
        return """from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass

from node_models import WorkflowNode


@dataclass(frozen=True)
class ForkLifecycle:
    fork_node_id: str
    generated_agents: int
    deleted_agents: int
    active_agents: int
    branch_width: int

    def to_dict(self) -> dict[str, int | str]:
        return asdict(self)


def build_fork_report(
    nodes: list[WorkflowNode],
    deleted_agents_by_fork: dict[str, int],
) -> list[ForkLifecycle]:
    report: list[ForkLifecycle] = []
    for node in nodes:
        if node.outgoing_edge_count <= 1:
            continue
        generated = node.outgoing_edge_count
        deleted = max(0, int(deleted_agents_by_fork.get(node.node_id, 0)))
        active = max(0, generated - deleted)
        report.append(
            ForkLifecycle(
                fork_node_id=node.node_id,
                generated_agents=generated,
                deleted_agents=deleted,
                active_agents=active,
                branch_width=node.outgoing_edge_count,
            )
        )
    return report


def summarize_compactions(compaction_events: list[dict[str, object]]) -> list[str]:
    lines: list[str] = []
    for event in compaction_events:
        node_id = str(event.get("node_id", "?"))
        summary = str(event.get("summary", ""))
        function_headers = int(event.get("function_header_count", 0))
        lines.append(f"{node_id}: {summary} (headers={function_headers})")
    return lines
"""

    if normalized.endswith("parallel_scheduler_demo/demo_runner.py"):
        return """from __future__ import annotations

import json

from fork_report import build_fork_report, summarize_compactions
from node_models import sample_graph
from prerequisite_counter import blocked_reason, ready_nodes


def run_demo() -> dict[str, object]:
    nodes = sample_graph()
    ready_after_root = [node.node_id for node in ready_nodes(nodes, {"A"})]
    ready_after_parallel = [node.node_id for node in ready_nodes(nodes, {"A", "B", "C"})]
    join_node = next(node for node in nodes if node.node_id == "D")

    compaction_events = [
        {
            "node_id": "B",
            "summary": "Left prerequisite branch compacted into readiness rules.",
            "function_header_count": 2,
        },
        {
            "node_id": "C",
            "summary": "Right reporting branch compacted into fork lifecycle summaries.",
            "function_header_count": 2,
        },
        {
            "node_id": "D",
            "summary": "Merge node compacted the parallel outputs into the final runnable truth.",
            "function_header_count": 1,
        },
    ]

    fork_report = [
        item.to_dict()
        for item in build_fork_report(nodes, deleted_agents_by_fork={"A": 2})
    ]

    return {
        "ready_after_root": ready_after_root,
        "ready_after_parallel": ready_after_parallel,
        "join_blocked_reason_after_partial_finish": blocked_reason(join_node, {"A", "B"}),
        "fork_report": fork_report,
        "compactions": summarize_compactions(compaction_events),
    }


def main() -> None:
    print(json.dumps(run_demo(), indent=2))


if __name__ == "__main__":
    main()
"""

    _MOCK_LOG.warning("_python_source_for: no match for target_file=%r (normalized=%r)", target_file, normalized)
    return "# mock provider did not recognize the requested target file\n"


def generate_text(runtime: ProviderRuntime, prompt: str) -> str:
    lowered = prompt.lower()
    request = _user_request(prompt)
    provider = runtime.provider_id.lower()
    if provider != "mock":
        raise ValueError(f"Mock agent only handles provider_id='mock', received '{runtime.provider_id}'")

    if "research agent for a model-context-protocol coding orchestrator" in lowered:
        return _research_response(request)

    if "\"graph_id\"" in prompt or "command_nodes" in prompt:
        return _planner_response()

    if "you are an expert code mutation agent." in lowered:
        return _python_source_for(_executor_target(prompt))

    _MOCK_LOG.warning(
        "generate_text: no pattern matched — returning echo fallback. "
        "provider=%r prompt_prefix=%r",
        runtime.provider_id,
        prompt[:120],
    )
    return json.dumps({"echo": request or "mock-provider-response"})


def generate_texts(runtime: ProviderRuntime, prompts: List[str]) -> List[str]:
    return [generate_text(runtime, prompt) for prompt in prompts]
