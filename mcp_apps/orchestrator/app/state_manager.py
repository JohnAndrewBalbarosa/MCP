from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from mcp_apps.orchestrator.libraries.types.contracts import DagGraph


@dataclass
class StateManager:
    graph: DagGraph
    events: List[dict] = field(default_factory=list)

    def mark_done(self, node_id: str) -> None:
        node = self.graph.node_by_id[node_id]
        node.status = "DONE"
        self.events.append({"event": "NODE_DONE", "node_id": node_id})

    def unblock_ready_nodes(self) -> List[str]:
        ready = []
        for node in self.graph.nodes:
            if node.status != "BLOCKED":
                continue
            finished_adjacent = sum(
                1 for dep in node.depends_on if self.graph.node_by_id[dep].status == "DONE"
            )
            required = node.incoming_flow_count or len(node.depends_on)
            if finished_adjacent >= required:
                node.status = "READY"
                ready.append(node.node_id)
        return ready
