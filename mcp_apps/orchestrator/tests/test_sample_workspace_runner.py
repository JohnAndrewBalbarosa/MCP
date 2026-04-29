from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from mcp_apps.orchestrator.app.sample_workspace_runner import (
    DEFAULT_WORKSPACE_ROOT,
    _scenario_root,
    run_parallel_scheduler_demo,
)


class SampleWorkspaceRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.addCleanup(self._remove_generated_scenario)

    def _remove_generated_scenario(self) -> None:
        scenario = _scenario_root(DEFAULT_WORKSPACE_ROOT)
        if scenario.exists():
            shutil.rmtree(scenario, ignore_errors=True)

    def test_parallel_scheduler_demo_generates_runnable_workspace_code(self) -> None:
        result = run_parallel_scheduler_demo()

        demo_output = result["demo_output"]
        generated_files = [Path(p) for p in result["generated_files"]]
        trace_root = Path(result["trace_root"])  # already a str, no extra str() needed

        # Node A forks into B and C — order is determined by graph traversal, not spec
        self.assertCountEqual(demo_output["ready_after_root"], ["B", "C"])
        self.assertCountEqual(demo_output["ready_after_parallel"], ["D"])

        fork = demo_output["fork_report"][0]
        self.assertEqual(fork["fork_node_id"], "A")
        self.assertEqual(fork["generated_agents"], 2)  # A spawns 2 branch agents (B, C)
        self.assertEqual(fork["deleted_agents"], 2)    # both retired after branching

        blocked = demo_output["join_blocked_reason_after_partial_finish"]
        self.assertIn("D waits for 2 prerequisites", blocked)

        for target in generated_files:
            self.assertTrue(target.exists(), f"missing generated file: {target}")

        self.assertTrue((trace_root / "planner" / "fork_agent_report.txt").exists())
        self.assertTrue((trace_root / "planner" / "compaction_report.txt").exists())


if __name__ == "__main__":
    unittest.main()
