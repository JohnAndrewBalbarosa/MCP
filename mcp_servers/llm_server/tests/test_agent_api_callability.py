from __future__ import annotations

import sys
import unittest
from unittest.mock import patch
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mcp_apps.orchestrator.libraries.types.contracts import SessionProfile
from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntimeView
from mcp_servers.llm_server.server import index
from mcp_servers.llm_server.server.agents.modules.defaults import default_model
from mcp_servers.llm_server.server.agents.vendors.registry import (
    get_batch_generator,
    get_provider_generator,
)


class TestLlmServerApiCallability(unittest.TestCase):
    """Validate that LLM server API entrypoints route to callable agent handlers."""

    def test_describe_research_runtime_routes_to_handler(self) -> None:
        expected = ProviderRuntimeView(
            provider_id="gemini",
            model="gemini-2.5-flash",
            max_output_tokens=1024,
            temperature=0.2,
            top_p=0.95,
            max_parallel_instances=1,
            max_context_lines=120,
        )
        with patch(
            "mcp_servers.llm_server.server.index.handle_describe_runtime",
            return_value=expected,
        ) as mocked:
            result = index.describe_research_runtime()

        mocked.assert_called_once_with("RESEARCH")
        self.assertEqual(result, expected)

    def test_describe_planner_runtime_routes_to_handler(self) -> None:
        expected = ProviderRuntimeView(
            provider_id="open-ai",
            model="gpt-4.1-mini",
            max_output_tokens=1024,
            temperature=0.2,
            top_p=0.95,
            max_parallel_instances=1,
            max_context_lines=120,
        )
        with patch(
            "mcp_servers.llm_server.server.index.handle_describe_runtime",
            return_value=expected,
        ) as mocked:
            result = index.describe_planner_runtime()

        mocked.assert_called_once_with("PLANNER")
        self.assertEqual(result, expected)

    def test_describe_executor_runtime_routes_to_handler(self) -> None:
        expected = ProviderRuntimeView(
            provider_id="qwen",
            model="Qwen/Qwen2.5-Coder-7B-Instruct",
            max_output_tokens=1024,
            temperature=0.2,
            top_p=0.95,
            max_parallel_instances=1,
            max_context_lines=120,
        )
        with patch(
            "mcp_servers.llm_server.server.index.handle_describe_runtime",
            return_value=expected,
        ) as mocked:
            result = index.describe_executor_runtime()

        mocked.assert_called_once_with("EXECUTOR")
        self.assertEqual(result, expected)

    def test_build_planner_session_profile_routes_to_handler(self) -> None:
        expected = SessionProfile(headers={"Authorization": "Bearer token"}, cookie_jar={})
        with patch(
            "mcp_servers.llm_server.server.index.handle_build_planner_session_profile",
            return_value=expected,
        ) as mocked:
            result = index.build_planner_session_profile()

        mocked.assert_called_once_with()
        self.assertEqual(result, expected)

    def test_generate_text_routes_to_role_handler(self) -> None:
        with patch(
            "mcp_servers.llm_server.server.index.handle_generate_text",
            return_value="ok",
        ) as mocked:
            research = index.generate_research_text("r")
            planner = index.generate_planner_text("p")
            executor = index.generate_executor_text("e")

        self.assertEqual(research, "ok")
        self.assertEqual(planner, "ok")
        self.assertEqual(executor, "ok")
        self.assertEqual(
            mocked.call_args_list,
            [
                (("RESEARCH", "r"), {}),
                (("PLANNER", "p"), {}),
                (("EXECUTOR", "e"), {}),
            ],
        )

    def test_generate_executor_texts_routes_to_batch_handler(self) -> None:
        prompts = ["a", "b"]
        with patch(
            "mcp_servers.llm_server.server.index.handle_generate_texts",
            return_value=["x", "y"],
        ) as mocked:
            result = index.generate_executor_texts(prompts)

        mocked.assert_called_once_with("EXECUTOR", prompts)
        self.assertEqual(result, ["x", "y"])

    def test_get_executor_context_limit_routes_to_handler(self) -> None:
        with patch(
            "mcp_servers.llm_server.server.index.handle_context_limit",
            return_value=2048,
        ) as mocked:
            result = index.get_executor_context_limit()

        mocked.assert_called_once_with("EXECUTOR")
        self.assertEqual(result, 2048)

    def test_provider_generator_callable_gemini(self) -> None:
        self.assertTrue(callable(get_provider_generator("gemini")))

    def test_provider_generator_callable_open_ai_alias(self) -> None:
        self.assertTrue(callable(get_provider_generator("open-ai")))

    def test_provider_generator_callable_openai(self) -> None:
        self.assertTrue(callable(get_provider_generator("openai")))

    def test_provider_generator_callable_qwen(self) -> None:
        self.assertTrue(callable(get_provider_generator("qwen")))

    def test_provider_generator_callable_huggingface(self) -> None:
        self.assertTrue(callable(get_provider_generator("huggingface")))

    def test_batch_generator_callable_qwen(self) -> None:
        self.assertTrue(callable(get_batch_generator("qwen")))

    def test_batch_generator_callable_hugging_face_alias(self) -> None:
        self.assertTrue(callable(get_batch_generator("hugging-face")))

    def test_batch_generator_none_for_gemini(self) -> None:
        self.assertIsNone(get_batch_generator("gemini"))

    def test_batch_generator_none_for_openai(self) -> None:
        self.assertIsNone(get_batch_generator("openai"))

    def test_default_model_gemini_is_gemini_2_5_flash(self) -> None:
        self.assertEqual(default_model("gemini", "RESEARCH"), "gemini-2.5-flash")

    def test_default_model_openai_is_gpt_4_1_mini(self) -> None:
        self.assertEqual(default_model("open-ai", "PLANNER"), "gpt-4.1-mini")

    def test_default_model_qwen_is_qwen_coder_7b(self) -> None:
        self.assertEqual(
            default_model("qwen", "EXECUTOR"),
            "Qwen/Qwen2.5-Coder-7B-Instruct",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
