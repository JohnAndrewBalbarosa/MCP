from __future__ import annotations

import json
import re
from dataclasses import dataclass

from mcp_clients.agent_executor.client.mcp_router import llm_generate_text
from mcp_apps.orchestrator.libraries.types.contracts import ResearchBrief


@dataclass
class ResearchAgent:
    """Generates a research brief that feeds the planner with structured context."""

    def build_research_prompt(self, request: str) -> str:
        return (
            "You are the research agent for a model-context-protocol coding orchestrator.\n"
            "Analyze the user request and return STRICT JSON only with these keys:\n"
            "  objective        - one-sentence goal\n"
            "  constraints      - list of hard constraints\n"
            "  assumptions      - list of contextual assumptions\n"
            "  risks            - list of risks\n"
            "  project_type     - short description "
            "of the app type you recommend\n"
            "  recommended_structure - ordered list "
            "of core folders/files to create\n"
            "  tech_stack       - exact technology stack to use "
            "(e.g. 'PHP/Laravel', 'Next.js/React/TypeScript').\n"
            "                     Infer the most appropriate modern stack from the request.\n"
            "  setup_commands   - ordered list of terminal commands "
            "to install or scaffold the project\n"
            "  run_commands     - ordered list of terminal commands "
            "to run/start the project\n"
            "  test_commands    - ordered list of terminal commands "
            "to run tests, matching the tech_stack\n"
            "IMPORTANT: All commands must match the tech_stack.\n"
            "If the request is for PHP, prefer Laravel unless the request "
            "explicitly asks for plain PHP.\n"
            "If the request is for a React/Next.js app, "
            "prefer Next.js with the App Router.\n"
            "Return exactly one JSON object. No markdown fences, "
            "no commentary, no trailing commas.\n"
            "Use empty arrays for lists that are not needed.\n"
            "Example shape: {\"objective\":\"...\","
            "\"constraints\":[],\"assumptions\":[],"
            "\"risks\":[],\"project_type\":\"...\","
            "\"recommended_structure\":[],\"tech_stack\":\"...\","
            "\"setup_commands\":[],\"run_commands\":[],"
            "\"test_commands\":[]}\n"
            f"User request:\n{request}\n"
        )

    def _research_repair_prompt(self, request: str, response_text: str) -> str:
        return (
            "Rewrite the previous response as valid JSON only.\n"
            "The output must contain exactly these keys: objective, "
            "constraints, assumptions, risks, project_type, "
            "recommended_structure, tech_stack, setup_commands, "
            "run_commands, test_commands.\n"
            "Do not add markdown fences, prose, or code blocks.\n"
            "Use empty arrays for list fields that are not needed.\n"
            "User request:\n"
            f"{request}\n\n"
            "Invalid response to repair:\n"
            f"{response_text}\n"
        )

    def _extract_json_object(self, text: str) -> dict | None:
        """Multi-pass JSON extraction:
        1. Strip any markdown fences regardless of position.
        2. Extract the outermost { ... } block.
        3. Parse as JSON.
        """
        if not text or not text.strip():
            return None

        # Pass 1: strip any ```json ... ``` fences wherever they appear
        cleaned = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        cleaned = re.sub(r"```", "", cleaned)
        cleaned = cleaned.strip()

        # Pass 2: find the outermost balanced { ... }
        start = cleaned.find("{")
        if start == -1:
            return None

        depth = 0
        end = -1
        for idx in range(start, len(cleaned)):
            if cleaned[idx] == "{":
                depth += 1
            elif cleaned[idx] == "}":
                depth -= 1
                if depth == 0:
                    end = idx
                    break

        if end == -1:
            return None

        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None

    def research(self, request: str) -> ResearchBrief:
        prompt = self.build_research_prompt(request)
        last_response = ""
        for attempt in range(2):
            response_text = llm_generate_text("RESEARCH", prompt)
            last_response = response_text
            payload = self._extract_json_object(response_text)
            if payload is None:
                prompt = self._research_repair_prompt(request, response_text)
                continue

            brief = ResearchBrief.from_dict(payload)
            if (
                not brief.objective.strip()
                or not brief.project_type.strip()
                or not brief.tech_stack.strip()
            ):
                prompt = self._research_repair_prompt(request, response_text)
                continue

            return brief

        raise RuntimeError(
            "Research agent did not return valid JSON after retries. "
            f"Last response: {last_response}"
        )
