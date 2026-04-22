from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mcp_apps.orchestrator.app.orchestrator import (
    _invalid_cwd_for_next_dot_target,
    _is_valid_npm_package_name,
    _normalize_command_for_execution,
)


class TestOrchestratorCommandNormalization(unittest.TestCase):
    def test_workspace_token_rewrites_to_current_root(self) -> None:
        command = 'npx create-next-app@latest "Workspace" --typescript --eslint --app'
        normalized = _normalize_command_for_execution(command)
        self.assertEqual(
            normalized,
            "npx create-next-app@latest . --typescript --eslint --app",
        )

    def test_valid_non_workspace_target_remains(self) -> None:
        command = "npx create-next-app@latest weather-app --typescript --eslint --app"
        normalized = _normalize_command_for_execution(command)
        self.assertEqual(normalized, command)

    def test_npm_name_validation_detects_uppercase_folder(self) -> None:
        self.assertFalse(_is_valid_npm_package_name("Workspace"))
        self.assertTrue(_is_valid_npm_package_name("workspace"))

    def test_invalid_cwd_for_dot_target_reports_actionable_message(self) -> None:
        message = _invalid_cwd_for_next_dot_target(
            "npx create-next-app@latest . --typescript --eslint --app",
            Path("C:/Users/Drew/Desktop/mcp/Workspace"),
        )
        self.assertIsNotNone(message)
        assert message is not None
        self.assertIn("not a valid npm package name", message)

    def test_invalid_cwd_for_dot_target_allows_lowercase_folder(self) -> None:
        message = _invalid_cwd_for_next_dot_target(
            "npx create-next-app@latest . --typescript --eslint --app",
            Path("C:/Users/Drew/Desktop/mcp/workspace"),
        )
        self.assertIsNone(message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
