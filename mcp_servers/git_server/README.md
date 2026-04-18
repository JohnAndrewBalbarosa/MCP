# Git MCP Server (Python)

Version-control service exposed through MCP server contracts.

## Responsibilities
- Provide git operations through a controlled server boundary.
- Keep git invocation logic out of clients and orchestrator nodes.
- Return normalized command output for orchestration decisions.

## Configuration
- Uses the shared root `.env` file.
- Runtime process variables override root `.env` values.
