# Orchestrator (Vendor-Neutral)

The orchestrator is the long-lived control plane for the MCP workflow.

## Responsibilities
- Run research and planning phases.
- Build and manage the DAG of command and mutation nodes.
- Schedule branch fan-out safely when parallel paths are available.
- Track node state transitions and aggregate execution results.

## Agent Tools Boundary
- Flow and response parsing tools are client-owned in
	`mcp_clients/agent_executor/tools/`.
- Orchestrator consumes parsed results and execution metadata.

## Boundaries
- The orchestrator does not execute vendor SDK calls directly.
- LLM generation is routed through MCP client routing to the server handler layer.
- File mutation is delegated to MCP servers using bounded line ranges.

## Configuration
- Uses the shared root `.env` file.
- Runtime process variables override root `.env` values.
