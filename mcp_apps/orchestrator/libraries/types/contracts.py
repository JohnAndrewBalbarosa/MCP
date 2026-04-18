from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any, Dict, List


def _string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if value in (None, ""):
        return []
    return [str(value)]


@dataclass
class ResearchBrief:
    objective: str
    constraints: List[str]
    assumptions: List[str]
    risks: List[str]
    project_type: str = ""
    recommended_structure: List[str] = field(default_factory=list)
    # Tech stack and lifecycle commands detected by the Research Agent.
    # These are the ONLY source of truth for terminal command nodes.
    tech_stack: str = ""                  # e.g. "Node.js/Express", "Python/FastAPI"
    setup_commands: List[str] = field(default_factory=list)   # e.g. ["npm install"]
    run_commands: List[str] = field(default_factory=list)     # e.g. ["npm run dev"]
    test_commands: List[str] = field(default_factory=list)    # e.g. ["npm test"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective": self.objective,
            "constraints": list(self.constraints),
            "assumptions": list(self.assumptions),
            "risks": list(self.risks),
            "project_type": self.project_type,
            "recommended_structure": list(self.recommended_structure),
            "tech_stack": self.tech_stack,
            "setup_commands": list(self.setup_commands),
            "run_commands": list(self.run_commands),
            "test_commands": list(self.test_commands),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ResearchBrief":
        return cls(
            objective=str(payload.get("objective", "")),
            constraints=_string_list(payload.get("constraints")),
            assumptions=_string_list(payload.get("assumptions")),
            risks=_string_list(payload.get("risks")),
            project_type=str(payload.get("project_type", "")),
            recommended_structure=_string_list(payload.get("recommended_structure")),
            tech_stack=str(payload.get("tech_stack", "")),
            setup_commands=_string_list(payload.get("setup_commands")),
            run_commands=_string_list(payload.get("run_commands")),
            test_commands=_string_list(payload.get("test_commands")),
        )


@dataclass
class DagNode:
    node_id: str
    status: str
    depends_on: List[str]
    next: List[str]
    target_file: str
    start_line: int
    end_line: int
    mutation_intent: str
    acceptance_checks: List[str]
    branch_key: str
    outgoing_flow_count: int = 0
    incoming_flow_count: int = 0
    task_type: str = "agent"
    terminal_command: str = ""
    command_scope: str = "workspace"


@dataclass
class DagGraph:
    graph_id: str
    nodes: List[DagNode]
    command_nodes: List[DagNode] = field(default_factory=list)
    created_at: str = ""

    def normalize_flow_counts(self) -> None:
        for node in self.nodes + self.command_nodes:
            node.outgoing_flow_count = len(node.next)
            node.incoming_flow_count = len(node.depends_on)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "created_at": self.created_at,
            "nodes": [
                {
                    "node_id": node.node_id,
                    "status": node.status,
                    "depends_on": list(node.depends_on),
                    "next": list(node.next),
                    "target_file": node.target_file,
                    "start_line": node.start_line,
                    "end_line": node.end_line,
                    "mutation_intent": node.mutation_intent,
                    "acceptance_checks": list(node.acceptance_checks),
                    "branch_key": node.branch_key,
                    "outgoing_flow_count": node.outgoing_flow_count,
                    "incoming_flow_count": node.incoming_flow_count,
                    "task_type": node.task_type,
                    "terminal_command": node.terminal_command,
                    "command_scope": node.command_scope,
                }
                for node in self.nodes
            ],
            "command_nodes": [
                {
                    "node_id": node.node_id,
                    "status": node.status,
                    "depends_on": list(node.depends_on),
                    "next": list(node.next),
                    "target_file": node.target_file,
                    "start_line": node.start_line,
                    "end_line": node.end_line,
                    "mutation_intent": node.mutation_intent,
                    "acceptance_checks": list(node.acceptance_checks),
                    "branch_key": node.branch_key,
                    "outgoing_flow_count": node.outgoing_flow_count,
                    "incoming_flow_count": node.incoming_flow_count,
                    "task_type": node.task_type,
                    "terminal_command": node.terminal_command,
                    "command_scope": node.command_scope,
                }
                for node in self.command_nodes
            ],
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "DagGraph":
        raw_nodes = payload.get("nodes", [])
        if not isinstance(raw_nodes, list):
            raw_nodes = []

        nodes: List[DagNode] = []
        for raw_node in raw_nodes:
            if not isinstance(raw_node, dict):
                continue

            node_id = str(raw_node.get("node_id", "")).strip()
            if not node_id:
                continue

            nodes.append(
                DagNode(
                    node_id=node_id,
                    status=str(raw_node.get("status", "BLOCKED")),
                    depends_on=_string_list(raw_node.get("depends_on")),
                    next=_string_list(raw_node.get("next")),
                    target_file=str(raw_node.get("target_file", "")),
                    start_line=int(raw_node.get("start_line", 0) or 0),
                    end_line=int(raw_node.get("end_line", 0) or 0),
                    mutation_intent=str(raw_node.get("mutation_intent", "")),
                    acceptance_checks=_string_list(raw_node.get("acceptance_checks")),
                    branch_key=str(raw_node.get("branch_key", "")),
                    outgoing_flow_count=int(raw_node.get("outgoing_flow_count", 0) or 0),
                    incoming_flow_count=int(raw_node.get("incoming_flow_count", 0) or 0),
                    task_type=str(
                        raw_node.get("task_type")
                        or raw_node.get("execution_mode")
                        or "agent"
                    ),
                    terminal_command=str(
                        raw_node.get("terminal_command")
                        or raw_node.get("command")
                        or ""
                    ),
                )
            )

        graph = cls(
            graph_id=str(payload.get("graph_id", "planner-plan")),
            nodes=nodes,
            command_nodes=[],
            created_at=str(payload.get("created_at", "")),
        )

        raw_command_nodes = payload.get("command_nodes", [])
        if not isinstance(raw_command_nodes, list):
            raw_command_nodes = []

        command_nodes: List[DagNode] = []
        for raw_node in raw_command_nodes:
            if not isinstance(raw_node, dict):
                continue

            node_id = str(raw_node.get("node_id", "")).strip()
            if not node_id:
                continue

            command_nodes.append(
                DagNode(
                    node_id=node_id,
                    status=str(raw_node.get("status", "BLOCKED")),
                    depends_on=_string_list(raw_node.get("depends_on")),
                    next=_string_list(raw_node.get("next")),
                    target_file=str(raw_node.get("target_file", "")),
                    start_line=int(raw_node.get("start_line", 0) or 0),
                    end_line=int(raw_node.get("end_line", 0) or 0),
                    mutation_intent=str(raw_node.get("mutation_intent", "")),
                    acceptance_checks=_string_list(raw_node.get("acceptance_checks")),
                    branch_key=str(raw_node.get("branch_key", "")),
                    outgoing_flow_count=int(raw_node.get("outgoing_flow_count", 0) or 0),
                    incoming_flow_count=int(raw_node.get("incoming_flow_count", 0) or 0),
                    task_type=str(
                        raw_node.get("task_type")
                        or raw_node.get("execution_mode")
                        or "command"
                    ),
                    terminal_command=str(
                        raw_node.get("terminal_command")
                        or raw_node.get("command")
                        or ""
                    ),
                    command_scope=str(raw_node.get("command_scope") or "workspace"),
                )
            )

        graph.command_nodes = command_nodes
        graph.normalize_flow_counts()
        return graph

    @property
    def node_by_id(self) -> Dict[str, DagNode]:
        return {node.node_id: node for node in self.nodes + self.command_nodes}


@dataclass
class SessionProfile:
    headers: Dict[str, str]
    cookie_jar: Dict[str, str]
