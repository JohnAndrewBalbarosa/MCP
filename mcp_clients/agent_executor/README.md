# Agent Executor (Vendor-Neutral)

The agent executor is the short-lived worker layer in the MCP workflow.

## Responsibilities
- Execute a single bounded DAG node at a time.
- Fetch only the allowed file snippet from the filesystem MCP server.
- Request code generation through the LLM MCP routing path.
- Apply deterministic bounded replacements through the filesystem MCP server.

## Agent Tools
- Response parsing, code-fence stripping, and function-summary extraction
	are implemented in `tools/response_parser.py`.
- Worker agent code in `client/worker.py` consumes the parser tool output.

## Boundaries
- No direct file writes.
- No vendor SDK calls from the client package.
- All model-specific behavior is isolated in the server agent vendor modules.

## Configuration
- Uses the shared root `.env` file.
- Runtime process variables override root `.env` values.
