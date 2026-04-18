# Filesystem MCP Server (Python)

Deterministic bounded read/write service for source edits.

## Responsibilities
- Return exact snippet ranges with `get_snippet(file, start_line, end_line)`.
- Apply exact bounded splices with `apply_snippet(file, start_line, end_line, replacement)`.
- Reject out-of-range edits.
- Use atomic writes and syntax checks where applicable.

## Position in Flow
client request -> server handler -> filesystem mutator.

## Configuration
- Uses the shared root `.env` file.
- Runtime process variables override root `.env` values.
