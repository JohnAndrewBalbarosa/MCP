from __future__ import annotations

import contextlib
import io
import threading
import unittest
from types import SimpleNamespace

from mcp_apps.orchestrator.app.planner import Planner
from mcp_apps.orchestrator.app.state_manager import StateManager
from mcp_apps.orchestrator.libraries.types.contracts import ResearchBrief
from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntime
from mcp_servers.llm_server.server import qwen_provider


class FakeInferenceClient:
    created_models: list[str] = []
    call_log: list[tuple[int, str]] = []
    barrier: threading.Barrier
    lock = threading.Lock()
    next_id = 0

    def __init__(self, model: str | None = None, token: str | None = None, provider: str | None = None) -> None:
        with self.__class__.lock:
            self.client_id = self.__class__.next_id
            self.__class__.next_id += 1
        self.model = model
        self.token = token
        self.provider = provider
        self.__class__.created_models.append(model or "")

    def chat_completion(self, messages, model=None, max_tokens=None, temperature=None, top_p=None):
        prompt = messages[0]["content"]
        with self.__class__.lock:
            self.__class__.call_log.append((self.client_id, prompt))
            call_count = len(self.__class__.call_log)
        barrier = getattr(self.__class__, "barrier", None)
        if barrier is not None and call_count <= 3:
            barrier.wait(timeout=5)
        if "code" in prompt.lower() or "function" in prompt.lower():
            content = (
                "def add_numbers(left: int, right: int) -> int:\n"
                "    return left + right\n"
            )
        else:
            content = f"client-{self.client_id}:{prompt}"
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content),
                )
            ]
        )


class RequirementTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_inference_client = qwen_provider.InferenceClient
        qwen_provider.InferenceClient = FakeInferenceClient
        qwen_provider._QWEN_POOLS.clear()
        FakeInferenceClient.created_models = []
        FakeInferenceClient.call_log = []
        FakeInferenceClient.barrier = threading.Barrier(3)
        FakeInferenceClient.next_id = 0

    def tearDown(self) -> None:
        qwen_provider.InferenceClient = self._original_inference_client
        qwen_provider._QWEN_POOLS.clear()

    def test_planner_can_fan_out_after_dependencies_clear(self) -> None:
        planner = Planner()
        graph = planner.plan(
            "parallelize the request when branches are independent",
            ResearchBrief(
                objective="Validate fan-out planning",
                constraints=["Keep it local"],
                assumptions=["Workspace exists"],
                risks=["Branch conflicts"],
            ),
        )

        state = StateManager(graph)

        self.assertEqual([node.node_id for node in graph.nodes if len(node.next) > 1], ["B"])
        self.assertEqual(state.mark_done("A"), None)
        self.assertEqual(state.unblock_ready_nodes(), ["B"])
        self.assertEqual(state.mark_done("B"), None)
        ready_after_b = state.unblock_ready_nodes()

        self.assertCountEqual(ready_after_b, ["C", "D"])
        self.assertEqual(graph.node_by_id["C"].depends_on, ["B"])
        self.assertEqual(graph.node_by_id["D"].depends_on, ["B"])
        self.assertNotEqual(graph.node_by_id["C"].branch_key, graph.node_by_id["D"].branch_key)

    def test_qwen_pool_uses_multiple_instances_for_parallel_requests(self) -> None:
        runtime = ProviderRuntime(
            provider_id="qwen",
            model="Qwen/Qwen2.5-Coder-7B-Instruct",
            api_key="token",
            max_output_tokens=32,
            temperature=0.2,
            top_p=0.95,
            max_parallel_instances=3,
            max_context_lines=16,
        )

        prompts = ["alpha", "beta", "gamma", "delta"]
        responses = qwen_provider.generate_texts(runtime, prompts)

        self.assertEqual(len(responses), 4)
        self.assertEqual(len(FakeInferenceClient.created_models), 3)
        self.assertEqual(len(FakeInferenceClient.call_log), 4)
        self.assertCountEqual([client_id for client_id, _ in FakeInferenceClient.call_log], [0, 1, 2, 0])
        self.assertCountEqual([prompt for _, prompt in FakeInferenceClient.call_log], prompts)
        self.assertTrue(all(response.startswith("client-") for response in responses))

    def test_qwen_can_generate_code_snippet(self) -> None:
        FakeInferenceClient.barrier = None
        runtime = ProviderRuntime(
            provider_id="qwen",
            model="Qwen/Qwen2.5-Coder-7B-Instruct",
            api_key="token",
            max_output_tokens=32,
            temperature=0.2,
            top_p=0.95,
            max_parallel_instances=1,
            max_context_lines=16,
        )

        generated = qwen_provider.generate_text(
            runtime,
            "Generate Python code for a small add_numbers function.",
        )

        print("\n=== Generated Code ===\n" + generated)
        self.assertIn("def add_numbers", generated)
        self.assertIn("return left + right", generated)

    def test_orchestrator_logs_plan_and_agent_timeline(self) -> None:
        from mcp_apps.orchestrator.app import orchestrator as orchestrator_module
        from mcp_apps.orchestrator.libraries.types.contracts import SessionProfile

        original_bootstrap = orchestrator_module.bootstrap_planner_session
        original_research_agent = orchestrator_module.ResearchAgent
        original_run_ephemeral_agent = orchestrator_module.run_ephemeral_agent

        class FakeResearchAgent:
            def research(self, request: str) -> ResearchBrief:
                return ResearchBrief(
                    objective=f"Research objective for: {request}",
                    constraints=["Keep output bounded"],
                    assumptions=["Sandbox workspace exists"],
                    risks=["Unbounded writes"],
                )

        def fake_bootstrap_planner_session() -> SessionProfile:
            return SessionProfile(headers={"Authorization": "Bearer planner-token"}, cookie_jar={})

        def fake_run_ephemeral_agent(agent_id: str, graph, node_id: str) -> dict:
            node = graph.node_by_id[node_id]
            return {
                "ok": True,
                "agent_id": agent_id,
                "node_id": node_id,
                "status": "DONE",
                "summary": f"generated code for {node.target_file} and created folder scaffold",
            }

        buffer = io.StringIO()
        try:
            orchestrator_module.bootstrap_planner_session = fake_bootstrap_planner_session
            orchestrator_module.ResearchAgent = FakeResearchAgent
            orchestrator_module.run_ephemeral_agent = fake_run_ephemeral_agent
            with contextlib.redirect_stdout(buffer):
                orchestrator_module.run_orchestrator(
                    "Generate code, create a folder, and create a plan for parallel work"
                )
        finally:
            orchestrator_module.bootstrap_planner_session = original_bootstrap
            orchestrator_module.ResearchAgent = original_research_agent
            orchestrator_module.run_ephemeral_agent = original_run_ephemeral_agent

        output = buffer.getvalue()
        self.assertIn("=== Planner Input ===", output)
        self.assertIn("Generate code, create a folder", output)
        self.assertIn("=== Planner Plan ===", output)
        self.assertIn("=== Planner Mermaid ===", output)
        self.assertIn("```mermaid", output)
        self.assertIn("flowchart TD", output)
        self.assertIn("=== Agent Timeline ===", output)
        self.assertIn("1. spawn agent-1 for node A", output)
        self.assertIn("2. dispatch agent-1 -> node A", output)
        self.assertIn("spawn agent-2 for node C", output)
        self.assertIn("spawn agent-3 for node D", output)
        self.assertIn("Agents used (ordered): agent-1, agent-2, agent-3", output)
        self.assertIn("Total agents used: 3", output)
        self.assertIn("generated code for", output)