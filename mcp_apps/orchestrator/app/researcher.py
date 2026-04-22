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
            "Always research prerequisites first and include bootstrap/scaffold commands "
            "before install/test/run commands.\n"
            "If the request is for PHP, prefer Laravel unless the request "
            "explicitly asks for plain PHP.\n"
            "If the request is for a React/Next.js app, "
            "prefer Next.js with the App Router.\n"
            "For scaffold commands like create-next-app, never use 'Workspace' or 'workspace' "
            "as the project name unless the user explicitly requests that literal name.\n"
            "If the project should be scaffolded in the current root, use '.' as the target.\n"
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

    def _fallback_research_brief(self, request: str, last_response: str) -> ResearchBrief:
        lowered = request.lower()

        if "laravel" in lowered or "php" in lowered:
            project_type = "Full-stack web app"
            tech_stack = "PHP/Laravel"
            recommended_structure = [
                "app/Http/Controllers",
                "resources/views",
                "routes/web.php",
                "database/migrations",
            ]
            setup_commands = ["composer install"]
            run_commands = ["php artisan serve"]
            test_commands = ["php artisan test"]
        elif "next" in lowered or "react" in lowered:
            project_type = "Full-stack web app"
            tech_stack = "Next.js/React/TypeScript"
            recommended_structure = [
                "app",
                "components",
                "lib",
                "public",
            ]
            setup_commands = [
                "npx create-next-app@latest . --typescript --eslint --app",
            ]
            run_commands = ["npm run dev"]
            test_commands = ["npm test"]
        elif "fastapi" in lowered or "python" in lowered:
            project_type = "API service"
            tech_stack = "Python/FastAPI"
            recommended_structure = [
                "app/main.py",
                "app/routes",
                "app/services",
                "tests",
            ]
            setup_commands = ["pip install -r requirements.txt"]
            run_commands = ["uvicorn app.main:app --reload"]
            test_commands = ["pytest"]
        else:
            project_type = "Service application"
            tech_stack = "Node.js/Express"
            recommended_structure = [
                "src/index.js",
                "src/routes",
                "src/services",
                "tests",
            ]
            setup_commands = ["npm init -y", "npm install express"]
            run_commands = ["npm run dev"]
            test_commands = ["npm test"]

        return self._normalize_lifecycle_commands(
            ResearchBrief(
            objective=(request.strip() or "Implement the requested feature set."),
            constraints=[
                "Return structured JSON outputs for planner consumption.",
                "Keep commands aligned with the selected tech stack.",
            ],
            assumptions=[
                "Workspace dependencies can be installed in the current environment.",
            ],
            risks=[
                "Initial research response was malformed or truncated.",
                f"Last invalid response excerpt: {last_response[:120]}",
            ],
            project_type=project_type,
            recommended_structure=recommended_structure,
            tech_stack=tech_stack,
            setup_commands=setup_commands,
            run_commands=run_commands,
            test_commands=test_commands,
            )
        )

    def _normalize_lifecycle_commands(self, brief: ResearchBrief) -> ResearchBrief:
        stack = brief.tech_stack.lower()

        setup = [str(cmd).strip() for cmd in brief.setup_commands if str(cmd).strip()]
        run = [str(cmd).strip() for cmd in brief.run_commands if str(cmd).strip()]
        tests = [str(cmd).strip() for cmd in brief.test_commands if str(cmd).strip()]

        def _prepend_missing(target: list[str], command: str) -> list[str]:
            if any(item.lower() == command.lower() for item in target):
                return target
            return [command, *target]

        def _append_missing(target: list[str], command: str) -> list[str]:
            if any(item.lower() == command.lower() for item in target):
                return target
            return [*target, command]

        def _normalize_scaffold_target(command: str) -> str:
            normalized = str(command).strip()
            if not normalized:
                return ""

            match = re.search(
                r"(?i)(\bcreate-next-app(?:@latest)?\b\s+)(\"[^\"]+\"|'[^']+'|\S+)(.*)",
                normalized,
            )
            if not match:
                return normalized

            token = match.group(2).strip().strip('"').strip("'")
            if not token:
                return normalized
            if token.startswith("-") or token == ".":
                return normalized
            if token.lower() == "workspace":
                return f"{normalized[: match.start(2)]}.{normalized[match.end(2):]}"

            safe = re.sub(r"[^a-z0-9._~-]", "-", token.strip().lower())
            safe = re.sub(r"-+", "-", safe).strip("-.") or "app"
            if safe == token:
                return normalized
            return f"{normalized[: match.start(2)]}{safe}{normalized[match.end(2):]}"

        setup = [_normalize_scaffold_target(cmd) for cmd in setup]
        run = [_normalize_scaffold_target(cmd) for cmd in run]
        tests = [_normalize_scaffold_target(cmd) for cmd in tests]

        if "next.js" in stack or "react" in stack:
            has_next_scaffold = any("create-next-app" in cmd.lower() for cmd in setup)
            if not has_next_scaffold:
                setup = _prepend_missing(
                    setup,
                    "npx create-next-app@latest . --typescript --eslint --app",
                )
            run = _append_missing(run, "npm run dev")
            tests = _append_missing(tests, "npm test")
        elif "node" in stack or "express" in stack:
            has_scaffold = any(
                token in cmd.lower()
                for cmd in setup
                for token in ("npm init", "create-", "npx")
            )
            if not has_scaffold:
                setup = _prepend_missing(setup, "npm init -y")
            if not any("npm install" in cmd.lower() for cmd in setup):
                setup = _append_missing(setup, "npm install")
            run = _append_missing(run, "npm run dev")
            tests = _append_missing(tests, "npm test")

        return ResearchBrief(
            objective=brief.objective,
            constraints=list(brief.constraints),
            assumptions=list(brief.assumptions),
            risks=list(brief.risks),
            project_type=brief.project_type,
            recommended_structure=list(brief.recommended_structure),
            tech_stack=brief.tech_stack,
            setup_commands=setup,
            run_commands=run,
            test_commands=tests,
        )

    def research(self, request: str) -> ResearchBrief:
        prompt = self.build_research_prompt(request)
        last_response = ""
        for attempt in range(3):
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

            return self._normalize_lifecycle_commands(brief)

        return self._fallback_research_brief(request, last_response)
