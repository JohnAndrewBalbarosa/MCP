from __future__ import annotations

import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mcp_apps.orchestrator.app.dag_builder import build_dag
from mcp_apps.orchestrator.app.orchestrator import run_orchestrator
from mcp_apps.orchestrator.libraries.types.contracts import DagGraph, DagNode, ResearchBrief, SessionProfile


class TestWorkspaceParallelExecution(unittest.TestCase):
    def test_workspace_parallel_graph_reports_fork_counts_and_compaction(self) -> None:
        workspace_root = REPO_ROOT / "Workspace"
        workspace_root.mkdir(exist_ok=True)

        brief = ResearchBrief(
            objective="Build a forked parser flow",
            constraints=[],
            assumptions=[],
            risks=[],
            tech_stack="Python",
        )

        raw_graph = DagGraph(
            graph_id="parallel-workspace",
            nodes=[
                DagNode(
                    node_id="A",
                    status="READY",
                    depends_on=[],
                    next=["B", "C"],
                    target_file="src/root.py",
                    start_line=1,
                    end_line=10,
                    mutation_intent="prepare shared root state",
                    acceptance_checks=[],
                    branch_key="root",
                ),
                DagNode(
                    node_id="B",
                    status="BLOCKED",
                    depends_on=["A"],
                    next=["D"],
                    target_file="src/left.py",
                    start_line=1,
                    end_line=10,
                    mutation_intent="implement left branch",
                    acceptance_checks=[],
                    branch_key="left",
                ),
                DagNode(
                    node_id="C",
                    status="BLOCKED",
                    depends_on=["A"],
                    next=["D"],
                    target_file="src/right.py",
                    start_line=1,
                    end_line=10,
                    mutation_intent="implement right branch",
                    acceptance_checks=[],
                    branch_key="right",
                ),
                DagNode(
                    node_id="D",
                    status="BLOCKED",
                    depends_on=["B", "C"],
                    next=[],
                    target_file="src/merge.py",
                    start_line=1,
                    end_line=10,
                    mutation_intent="merge branch outputs",
                    acceptance_checks=[],
                    branch_key="merge",
                ),
            ],
        )
        graph = build_dag(
            raw_graph,
            workspace_context=None,
            research_brief=brief,
            executor_max_span_lines=16,
        )

        seen_contexts: dict[str, list[str]] = {}

        def fake_execute_node(
            agent_id: str,
            graph,
            node_id: str,
            abstraction_context: list[str] | None = None,
            enforce_layered_design: bool = True,
        ) -> dict:
            del agent_id
            del graph
            del enforce_layered_design
            seen_contexts[node_id] = list(abstraction_context or [])
            return {
                "ok": True,
                "status": "DONE",
                "summary": f"{node_id} complete",
                "artifact_summary_text": f"{node_id} compact summary",
                "artifact_summary": {
                    "branch_summary": f"{node_id} branch summary",
                    "function_headers": [
                        {
                            "name": f"fn_{node_id.lower()}",
                            "description": f"{node_id} function",
                            "input": f"{node_id.lower()}_input",
                            "output": f"{node_id.lower()}_output",
                        }
                    ],
                    "known_inputs": [f"{node_id.lower()}_input"],
                    "known_outputs": [f"{node_id.lower()}_output"],
                    "known_constraints": [f"{node_id.lower()}_constraint"],
                    "replacement_head": f"{node_id} replacement head",
                },
            }

        old_cwd = Path.cwd()
        old_trace = os.environ.get("MCP_TRACE_EXPORT_DIR")
        old_layered = os.environ.get("MCP_IMPLICIT_LAYERED_DESIGN")
        trace_dir = workspace_root / "__trace_parallel_test__"
        src = workspace_root / "parallel_test_case" / "src"
        try:
            os.chdir(workspace_root)
            os.environ["MCP_IMPLICIT_LAYERED_DESIGN"] = "1"
            os.environ["MCP_TRACE_EXPORT_DIR"] = str(trace_dir)

            shutil.rmtree(trace_dir, ignore_errors=True)
            shutil.rmtree(src.parent, ignore_errors=True)
            src.mkdir(parents=True, exist_ok=True)
            for name in ("root.py", "left.py", "right.py", "merge.py"):
                (src / name).write_text("# placeholder\n", encoding="utf-8")

            with patch(
                "mcp_apps.orchestrator.app.orchestrator.bootstrap_planner_session",
                return_value=SessionProfile(headers={}, cookie_jar={}),
            ), patch(
                "mcp_apps.orchestrator.app.orchestrator.ResearchAgent.research",
                return_value=brief,
            ), patch(
                "mcp_apps.orchestrator.app.orchestrator.Planner.plan",
                return_value=graph,
            ), patch(
                "mcp_apps.orchestrator.app.orchestrator.execute_node",
                side_effect=fake_execute_node,
            ):
                run_orchestrator("Build a task with parallel branches and a merge prerequisite")

            trace_root = trace_dir / "planner"
            parallel_waves = (trace_root / "parallel_waves.txt").read_text(encoding="utf-8")
            fork_report = (trace_root / "fork_agent_report.txt").read_text(encoding="utf-8")
            compaction_report = (trace_root / "compaction_report.txt").read_text(encoding="utf-8")
            abstraction_report = (trace_root / "abstraction_summaries.txt").read_text(encoding="utf-8")

            self.assertIn("Wave 2: B, C", parallel_waves)
            self.assertIn("- A: generated=2 retired=2 active=0", fork_report)
            self.assertIn("node=B", compaction_report)
            self.assertIn("node=C", compaction_report)
            self.assertIn("node=D", compaction_report)
            self.assertIn("function: fn_b", abstraction_report)
            self.assertIn("function: fn_c", abstraction_report)

            self.assertEqual(seen_contexts["A"], [])
            self.assertTrue(any("file: src/root.py" in item for item in seen_contexts["B"]))
            self.assertTrue(any("file: src/root.py" in item for item in seen_contexts["C"]))
            self.assertTrue(any("file: src/left.py" in item for item in seen_contexts["D"]))
            self.assertTrue(any("file: src/right.py" in item for item in seen_contexts["D"]))
        finally:
            os.chdir(old_cwd)
            shutil.rmtree(trace_dir, ignore_errors=True)
            shutil.rmtree(src.parent, ignore_errors=True)
            if old_trace is None:
                os.environ.pop("MCP_TRACE_EXPORT_DIR", None)
            else:
                os.environ["MCP_TRACE_EXPORT_DIR"] = old_trace
            if old_layered is None:
                os.environ.pop("MCP_IMPLICIT_LAYERED_DESIGN", None)
            else:
                os.environ["MCP_IMPLICIT_LAYERED_DESIGN"] = old_layered


if __name__ == "__main__":
    unittest.main(verbosity=2)
