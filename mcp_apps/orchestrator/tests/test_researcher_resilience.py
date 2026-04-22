from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mcp_apps.orchestrator.app.researcher import ResearchAgent


class TestResearcherResilience(unittest.TestCase):
    def test_truncated_json_falls_back_to_deterministic_brief(self) -> None:
        agent = ResearchAgent()
        request = "Create a full-stack weather report application using Next.js and Node.js"

        truncated = '{"objective":"Create weather app","constraints":['
        with patch(
            "mcp_apps.orchestrator.app.researcher.llm_generate_text",
            return_value=truncated,
        ):
            brief = agent.research(request)

        self.assertTrue(brief.objective)
        self.assertEqual(brief.tech_stack, "Next.js/React/TypeScript")
        self.assertTrue(brief.project_type)
        self.assertTrue(brief.setup_commands)
        self.assertTrue(brief.run_commands)

    def test_node_stack_includes_prerequisite_init_command(self) -> None:
        agent = ResearchAgent()
        payload = (
            '{'
            '"objective":"x",'
            '"constraints":[],"assumptions":[],"risks":[],'
            '"project_type":"Service application",'
            '"recommended_structure":["src/index.js"],'
            '"tech_stack":"Node.js/Express",'
            '"setup_commands":["npm install"],'
            '"run_commands":["npm run dev"],'
            '"test_commands":["npm test"]'
            '}'
        )

        with patch(
            "mcp_apps.orchestrator.app.researcher.llm_generate_text",
            return_value=payload,
        ):
            brief = agent.research("build website")

        self.assertEqual(brief.setup_commands[0], "npm init -y")
        self.assertIn("npm install", brief.setup_commands)

    def test_next_stack_includes_scaffold_command(self) -> None:
        agent = ResearchAgent()
        payload = (
            '{'
            '"objective":"x",'
            '"constraints":[],"assumptions":[],"risks":[],'
            '"project_type":"Web app",'
            '"recommended_structure":["app/page.tsx"],'
            '"tech_stack":"Next.js/React/TypeScript",'
            '"setup_commands":["npm install"],'
            '"run_commands":["npm run dev"],'
            '"test_commands":["npm test"]'
            '}'
        )

        with patch(
            "mcp_apps.orchestrator.app.researcher.llm_generate_text",
            return_value=payload,
        ):
            brief = agent.research("build next app")

        self.assertIn("create-next-app", brief.setup_commands[0])

    def test_next_stack_normalizes_workspace_target_to_current_root(self) -> None:
        agent = ResearchAgent()
        payload = (
            '{'
            '"objective":"x",'
            '"constraints":[],"assumptions":[],"risks":[],'
            '"project_type":"Web app",'
            '"recommended_structure":["app/page.tsx"],'
            '"tech_stack":"Next.js/React/TypeScript",'
            '"setup_commands":["npx create-next-app@latest \"Workspace\" --typescript --eslint --app"],'
            '"run_commands":["npm run dev"],'
            '"test_commands":["npm test"]'
            '}'
        )

        with patch(
            "mcp_apps.orchestrator.app.researcher.llm_generate_text",
            return_value=payload,
        ):
            brief = agent.research("build next app")

        self.assertEqual(
            brief.setup_commands[0],
            "npx create-next-app@latest . --typescript --eslint --app",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
