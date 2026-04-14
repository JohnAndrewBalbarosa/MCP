from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ProviderConfig:
    provider_id: str
    api_url: str


@dataclass
class ResearchBrief:
    objective: str
    constraints: List[str]
    assumptions: List[str]
    risks: List[str]


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


@dataclass
class DagGraph:
    graph_id: str
    nodes: List[DagNode]

    @property
    def node_by_id(self) -> Dict[str, DagNode]:
        return {node.node_id: node for node in self.nodes}


@dataclass
class SessionProfile:
    base_url: str
    headers: Dict[str, str]
    cookie_jar: Dict[str, str]
