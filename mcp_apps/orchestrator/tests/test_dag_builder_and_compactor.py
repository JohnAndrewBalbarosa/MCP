from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mcp_apps.orchestrator.app.context_compactor import compact_branch_context
from mcp_apps.orchestrator.app.dag_builder import build_dag
from mcp_apps.orchestrator.libraries.auth.api_converter import normalize_api_request
from mcp_apps.orchestrator.libraries.types.contracts import DagGraph, DagNode, ResearchBrief


class TestDagBuilderAndCompactor(unittest.TestCase):
    def test_build_dag_marks_branch_merge_and_parallel_metadata(self) -> None:
        graph = DagGraph(
            graph_id="g",
            nodes=[
                DagNode(
                    node_id="A",
                    status="READY",
                    depends_on=[],
                    next=["B", "C"],
                    target_file="src/a.py",
                    start_line=1,
                    end_line=20,
                    mutation_intent="build A",
                    acceptance_checks=[],
                    branch_key="root",
                ),
                DagNode(
                    node_id="B",
                    status="BLOCKED",
                    depends_on=["A"],
                    next=["D"],
                    target_file="src/b.py",
                    start_line=1,
                    end_line=20,
                    mutation_intent="build B",
                    acceptance_checks=[],
                    branch_key="left",
                ),
                DagNode(
                    node_id="C",
                    status="BLOCKED",
                    depends_on=["A"],
                    next=["D"],
                    target_file="src/c.py",
                    start_line=1,
                    end_line=20,
                    mutation_intent="build C",
                    acceptance_checks=[],
                    branch_key="right",
                ),
                DagNode(
                    node_id="D",
                    status="BLOCKED",
                    depends_on=["B", "C"],
                    next=[],
                    target_file="src/d.py",
                    start_line=1,
                    end_line=20,
                    mutation_intent="merge D",
                    acceptance_checks=[],
                    branch_key="merge",
                ),
            ],
        )

        finalized = build_dag(
            graph,
            workspace_context=None,
            research_brief=ResearchBrief(
                objective="x",
                constraints=[],
                assumptions=[],
                risks=[],
            ),
            executor_max_span_lines=16,
        )

        node_a = finalized.node_by_id["A"]
        node_b = finalized.node_by_id["B"]
        node_c = finalized.node_by_id["C"]
        node_d = finalized.node_by_id["D"]

        self.assertEqual(node_a.outgoing_flow_count, 2)
        self.assertEqual(node_d.incoming_flow_count, 2)
        self.assertEqual(node_a.merge_role, "branch")
        self.assertEqual(node_d.merge_role, "merge")
        self.assertEqual(node_b.parallel_group, "wave-2")
        self.assertEqual(node_c.parallel_group, "wave-2")
        self.assertTrue(node_b.requires_fresh_agent)
        self.assertTrue(node_d.requires_fresh_agent)
        self.assertEqual(node_d.handoff_strategy, "ground_truth")

    def test_compact_branch_context_builds_ground_truth_packet(self) -> None:
        packet = compact_branch_context(
            node_id="A",
            target_file="app/main.py",
            branch_outputs=["file=app/main.py | intent=add route"],
            artifact_summary={
                "branch_summary": "Added request handling path",
                "function_headers": [
                    {
                        "name": "handle_request",
                        "description": "Process one inbound request",
                        "input": "request",
                        "output": "response",
                    }
                ],
                "known_inputs": ["request"],
                "known_outputs": ["response"],
                "known_constraints": ["must stay line-bounded"],
            },
            node_metadata={
                "requires_fresh_agent": True,
                "merge_role": "merge",
                "incoming_flow_count": 2,
            },
        )

        self.assertTrue(packet["requires_fresh_agent"])
        ground_truth = packet["next_agent_ground_truth"]
        self.assertIn("file: app/main.py", ground_truth)
        self.assertIn("summary: Added request handling path", ground_truth)
        self.assertIn("function: handle_request", ground_truth)
        self.assertIn("input: request", ground_truth)
        self.assertIn("output: response", ground_truth)

    def test_normalize_api_request_is_api_only_and_sanitizes_headers(self) -> None:
        normalized = normalize_api_request(
            {
                "url": "https://example.com/api",
                "method": "post",
                "headers": {
                    "Authorization": "Bearer token",
                    "Host": "example.com",
                    "Content-Length": "12",
                },
                "query_params": {"q": "x"},
                "body": {"ok": True},
            }
        )

        self.assertEqual(normalized["method"], "POST")
        self.assertEqual(normalized["query_params"], {"q": "x"})
        self.assertEqual(normalized["body_template"], {"ok": True})
        self.assertEqual(normalized["headers"], {"Authorization": "Bearer token"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
