from __future__ import annotations

from dataclasses import dataclass

from mcp_apps.orchestrator.libraries.providers.research_provider_factory import select_research_provider
from mcp_servers.llm_server.server.index import generate_research_text
from mcp_apps.orchestrator.libraries.types.contracts import ResearchBrief


@dataclass
class ResearchAgent:
    """Generates a research brief that feeds the planner with structured context."""

    def research(self, request: str) -> ResearchBrief:
        selection = select_research_provider()
        summary = generate_research_text(
            "Return a compact coding research brief with constraints, assumptions, and risks. "
            f"Task: {request}"
        )
        return ResearchBrief(
            objective=summary or f"Research objective via {selection.provider_id}: {request}",
            constraints=["Respect strict line-bounded edits", "No out-of-scope file changes"],
            assumptions=["Codebase metadata is available", "MCP servers are reachable"],
            risks=["Ambiguous requirements", "Cross-file dependency surprises"],
        )
