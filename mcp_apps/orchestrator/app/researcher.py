from __future__ import annotations

from dataclasses import dataclass

from mcp_apps.orchestrator.libraries.providers.research_provider_factory import select_research_provider
from mcp_apps.orchestrator.libraries.types.contracts import ResearchBrief


@dataclass
class ResearchAgent:
    """Generates a research brief that feeds the planner with structured context."""

    def research(self, request: str) -> ResearchBrief:
        selection = select_research_provider()
        # Placeholder for provider-specific research call.
        return ResearchBrief(
            objective=f"Research objective via {selection.provider_id}: {request}",
            constraints=["Respect strict line-bounded edits", "No out-of-scope file changes"],
            assumptions=["Codebase metadata is available", "MCP servers are reachable"],
            risks=["Ambiguous requirements", "Cross-file dependency surprises"],
        )
