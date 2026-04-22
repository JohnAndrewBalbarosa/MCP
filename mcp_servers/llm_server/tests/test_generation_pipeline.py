from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mcp_clients.agent_executor.client import mcp_router
from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntime
from mcp_servers.llm_server.server.agents import entrypoint


class TestGenerationPipeline(unittest.TestCase):
    def test_entrypoint_returns_provider_response(self) -> None:
        runtime = ProviderRuntime(provider_id="openai", model="gpt-test", api_key="token")
        provider_generate = Mock(return_value="model-response")

        with patch(
            "mcp_servers.llm_server.server.agents.entrypoint.load_runtime",
            return_value=runtime,
        ) as mocked_runtime, patch(
            "mcp_servers.llm_server.server.agents.entrypoint.get_provider_generator",
            return_value=provider_generate,
        ) as mocked_registry, patch(
            "mcp_servers.llm_server.server.agents.entrypoint.log_generation",
        ) as mocked_log:
            response = entrypoint.generate_text("EXECUTOR", "ping model")

        self.assertEqual(response, "model-response")
        mocked_runtime.assert_called_once_with("EXECUTOR")
        mocked_registry.assert_called_once_with("openai")
        provider_generate.assert_called_once_with(runtime, "ping model")
        mocked_log.assert_called_once_with(
            "executor",
            "openai",
            "gpt-test",
            "ping model",
            "model-response",
        )

    def test_client_router_pipelines_prompt_to_handler_unchanged(self) -> None:
        with patch(
            "mcp_clients.agent_executor.client.mcp_router.load_env",
            return_value={"LLM_MCP_URL": "http://127.0.0.1:8103"},
        ), patch(
            "mcp_clients.agent_executor.client.mcp_router._rate_limit_llm_requests",
        ) as mocked_rate_limit, patch(
            "mcp_clients.agent_executor.client.mcp_router.handle_generate_text",
            return_value="handler-response",
        ) as mocked_handler:
            response = mcp_router.llm_generate_text(
                "PLANNER",
                "pipeline this exact prompt",
            )

        self.assertEqual(response, "handler-response")
        mocked_rate_limit.assert_called_once_with()
        mocked_handler.assert_called_once_with(
            "PLANNER",
            "pipeline this exact prompt",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
