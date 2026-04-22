from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mcp_apps.orchestrator.app.planner import Planner
from mcp_apps.orchestrator.libraries.types.contracts import DagGraph, DagNode, ResearchBrief
from mcp_clients.agent_executor.libraries.types.contracts import ProviderRuntimeView


class TestPlannerCommandHelpers(unittest.TestCase):
    def test_collect_terminal_commands_dedupes_in_order(self) -> None:
        planner = Planner()
        brief = ResearchBrief(
            objective="x",
            constraints=[],
            assumptions=[],
            risks=[],
            setup_commands=["npm install", "npm install"],
            run_commands=["npm run dev"],
            test_commands=["npm test", "npm run dev"],
        )

        commands = planner._collect_terminal_commands(brief)
        self.assertEqual(commands, ["npm install", "npm run dev", "npm test"])

    def test_build_command_nodes_builds_sequential_flow(self) -> None:
        planner = Planner()
        nodes = planner._build_command_nodes(["a", "b", "c"])

        self.assertEqual([n.node_id for n in nodes], ["CMD-01", "CMD-02", "CMD-03"])
        self.assertEqual(nodes[0].status, "READY")
        self.assertEqual(nodes[1].status, "BLOCKED")
        self.assertEqual(nodes[0].next, ["CMD-02"])
        self.assertEqual(nodes[1].depends_on, ["CMD-01"])
        self.assertEqual(nodes[2].depends_on, ["CMD-02"])
        self.assertEqual(nodes[2].next, [])

    def test_collect_terminal_commands_normalizes_next_project_name(self) -> None:
        planner = Planner()
        brief = ResearchBrief(
            objective="x",
            constraints=[],
            assumptions=[],
            risks=[],
            setup_commands=["npx create-next-app@latest Workspace --typescript --eslint --app"],
            run_commands=[],
            test_commands=[],
        )

        commands = planner._collect_terminal_commands(brief)
        self.assertEqual(
            commands,
            ["npx create-next-app@latest . --typescript --eslint --app"],
        )

    def test_collect_terminal_commands_normalizes_quoted_workspace_name(self) -> None:
        planner = Planner()
        brief = ResearchBrief(
            objective="x",
            constraints=[],
            assumptions=[],
            risks=[],
            setup_commands=["npx create-next-app@latest \"Workspace\" --typescript --eslint --app"],
            run_commands=[],
            test_commands=[],
        )

        commands = planner._collect_terminal_commands(brief)
        self.assertEqual(
            commands,
            ["npx create-next-app@latest . --typescript --eslint --app"],
        )

    def test_collect_terminal_commands_skips_scaffold_when_workspace_exists(self) -> None:
        planner = Planner()
        brief = ResearchBrief(
            objective="x",
            constraints=[],
            assumptions=[],
            risks=[],
            setup_commands=["npx create-next-app@latest Workspace --typescript --eslint --app"],
            run_commands=["npm run dev"],
            test_commands=["npm test"],
        )
        workspace_context = {
            "cwd_entries": ["app/", "components/", "package.json"],
            "files": [
                {"path": "app/page.tsx", "preview": ""},
                {"path": "app/layout.tsx", "preview": ""},
                {"path": "package.json", "preview": "{}"},
            ],
        }

        commands = planner._collect_terminal_commands(
            brief,
            workspace_context=workspace_context,
        )
        self.assertEqual(commands, ["npm run dev", "npm test"])

    def test_describe_terminal_commands_uses_research_brief_commands(self) -> None:
        planner = Planner()
        graph = DagGraph(graph_id="g", nodes=[])
        brief = ResearchBrief(
            objective="x",
            constraints=[],
            assumptions=[],
            risks=[],
            setup_commands=["npm install"],
            run_commands=["npm run dev"],
            test_commands=["npm test"],
        )

        rendered = planner.describe_terminal_commands(graph, research_brief=brief)
        self.assertIn("1. npm install", rendered)
        self.assertIn("2. npm run dev", rendered)
        self.assertIn("3. npm test", rendered)

    def test_plan_uses_fallback_graph_when_planner_json_invalid(self) -> None:
        planner = Planner()
        brief = ResearchBrief(
            objective="Build weather app",
            constraints=[],
            assumptions=[],
            risks=[],
            project_type="Web app",
            recommended_structure=["app/page.tsx", "package.json", "next.config.js"],
            tech_stack="Next.js/React/TypeScript",
            setup_commands=["npm install"],
            run_commands=["npm run dev"],
            test_commands=["npm test"],
        )

        with patch(
            "mcp_apps.orchestrator.app.planner.llm_generate_text",
            return_value='```json\n{"graph_id": "broken", "nodes": [',
        ):
            graph = planner.plan("build weather", brief, workspace_context=None)

        self.assertEqual(graph.graph_id, "planner-fallback")
        self.assertTrue(graph.nodes)
        self.assertTrue(graph.command_nodes)

    def test_plan_filters_existing_workspace_scaffold_command_nodes(self) -> None:
        planner = Planner()
        brief = ResearchBrief(
            objective="Build weather app",
            constraints=[],
            assumptions=[],
            risks=[],
            project_type="Web app",
            recommended_structure=["app/page.tsx"],
            tech_stack="Next.js/React/TypeScript",
            setup_commands=[],
            run_commands=["npm run dev"],
            test_commands=["npm test"],
        )

        workspace_context = {
            "cwd_entries": ["app/", "components/", "lib/", "package.json"],
            "files": [
                {"path": "app/page.tsx", "preview": ""},
                {"path": "app/layout.tsx", "preview": ""},
                {"path": "package.json", "preview": "{}"},
            ],
        }

        planner_json = json.dumps(
            {
                "graph_id": "g",
                "created_at": "2026-01-01T00:00:00Z",
                "nodes": [
                    {
                        "node_id": "A",
                        "status": "READY",
                        "depends_on": [],
                        "next": [],
                        "target_file": "app/page.tsx",
                        "start_line": 1,
                        "end_line": 20,
                        "mutation_intent": "x",
                        "acceptance_checks": [],
                        "branch_key": "b",
                        "task_type": "agent",
                        "terminal_command": "",
                        "command_scope": "workspace",
                    }
                ],
                "command_nodes": [
                    {
                        "node_id": "CMD-01",
                        "status": "READY",
                        "depends_on": [],
                        "next": [],
                        "target_file": "",
                        "start_line": 0,
                        "end_line": 0,
                        "mutation_intent": "cmd",
                        "acceptance_checks": [],
                        "branch_key": "command-flow",
                        "task_type": "command",
                        "terminal_command": (
                            "npx create-next-app@latest \"Workspace\" "
                            "--typescript --eslint --app"
                        ),
                        "command_scope": "workspace",
                    }
                ],
            }
        )

        with patch(
            "mcp_apps.orchestrator.app.planner.llm_generate_text",
            return_value=planner_json,
        ), patch(
            "mcp_apps.orchestrator.app.planner.llm_describe_runtime",
            return_value=ProviderRuntimeView(
                provider_id="qwen",
                model="Qwen/Qwen2.5-Coder-7B-Instruct",
                max_output_tokens=512,
                temperature=0.2,
                top_p=0.95,
                max_parallel_instances=4,
                max_context_lines=16,
            ),
        ):
            graph = planner.plan(
                "build weather",
                brief,
                workspace_context=workspace_context,
            )

        self.assertEqual(graph.command_nodes, [])

    def test_finalize_graph_clamps_span_to_executor_limit(self) -> None:
        planner = Planner()
        graph = DagGraph(
            graph_id="g",
            nodes=[
                DagNode(
                    node_id="A",
                    status="READY",
                    depends_on=[],
                    next=[],
                    target_file="src/index.js",
                    start_line=1,
                    end_line=80,
                    mutation_intent="x",
                    acceptance_checks=[],
                    branch_key="b",
                )
            ],
        )

        with patch(
            "mcp_apps.orchestrator.app.planner.llm_describe_runtime",
            return_value=ProviderRuntimeView(
                provider_id="qwen",
                model="Qwen/Qwen2.5-Coder-7B-Instruct",
                max_output_tokens=512,
                temperature=0.2,
                top_p=0.95,
                max_parallel_instances=4,
                max_context_lines=16,
            ),
        ):
            finalized = planner._finalize_graph(graph)

        self.assertEqual(finalized.nodes[0].start_line, 1)
        self.assertEqual(finalized.nodes[0].end_line, 16)

    def test_finalize_graph_forces_command_first_execution(self) -> None:
        planner = Planner()
        graph = DagGraph(
            graph_id="g",
            nodes=[
                DagNode(
                    node_id="A",
                    status="READY",
                    depends_on=[],
                    next=["CMD-01"],
                    target_file="src/index.js",
                    start_line=1,
                    end_line=20,
                    mutation_intent="x",
                    acceptance_checks=[],
                    branch_key="b",
                )
            ],
            command_nodes=[
                DagNode(
                    node_id="CMD-01",
                    status="BLOCKED",
                    depends_on=["A"],
                    next=[],
                    target_file="",
                    start_line=0,
                    end_line=0,
                    mutation_intent="cmd",
                    acceptance_checks=[],
                    branch_key="command-flow",
                    task_type="command",
                    terminal_command="npm install",
                    command_scope="workspace",
                )
            ],
        )

        with patch(
            "mcp_apps.orchestrator.app.planner.llm_describe_runtime",
            return_value=ProviderRuntimeView(
                provider_id="qwen",
                model="Qwen/Qwen2.5-Coder-7B-Instruct",
                max_output_tokens=512,
                temperature=0.2,
                top_p=0.95,
                max_parallel_instances=4,
                max_context_lines=16,
            ),
        ):
            finalized = planner._finalize_graph(graph)

        self.assertEqual(finalized.command_nodes[0].status, "READY")
        self.assertEqual(finalized.nodes[0].depends_on, ["CMD-01"])
        self.assertEqual(finalized.nodes[0].status, "BLOCKED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
