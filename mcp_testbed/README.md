# MCP Testbed

Isolated sandbox for testing the MCP stack without putting test inputs or outputs inside `mcp_apps`, `mcp_clients`, or `mcp_servers`.

## Layout
- `input/` holds the request text and any case-specific test artifacts.
- `output/` holds the active run while it is executing, then archives the finished logs into `output/batch_logs/<timestamp>/` and clears the active `.log` files for the next run.
- `workspace/` is the disposable working copy the orchestrator mutates during a test run.

## Workflow
1. Activate the virtual environment for the repo and install dependencies from [requirements.txt](../requirements.txt).
2. Put the test request in [input/request.txt](input/request.txt) or create another request file under [input](input).
3. Start the MCP services from the main repo in separate terminals using your normal launch commands.
4. Run [run_case.ps1](run_case.ps1) from the repo root. The runner will use the repo `.venv` when it exists, execute against `workspace/`, and then run the requirement tests.
5. Read the archived execution log from the newest folder under `output/batch_logs/`. The runner keeps raw API and requirement output there, then clears the active log files so the next test starts clean.
6. Replace the request file for the next case, or pass a different file to the runner with the RequestFile parameter.

## Rules
- Keep this folder decoupled from the MCP source folders.
- Do not write test artifacts into `mcp_apps`, `mcp_clients`, or `mcp_servers`.
- If you later turn this into a VS Code extension, point the extension at this sandbox folder as the test workspace root.
